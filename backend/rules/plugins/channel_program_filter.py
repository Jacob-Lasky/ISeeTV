"""Channel Program Filter Plugin.

This plugin filters out channels if all their programs have been filtered out
within the next X hours. This helps remove channels that have no viable content
in the near future.

Architecture:
- Atomic Design: Single responsibility for channel-program relationship filtering
- Cross-table Analysis: Examines both channels and their associated programs
- Time-based Logic: Configurable time window for program analysis
- Database Efficient: Uses optimized queries to check program availability
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Union

from sqlalchemy import and_, text
from sqlalchemy.orm import Session

from common.log_utils import get_logger
from models.models import EpgChannel, M3uChannel, Program
from rules.plugins import BasePlugin, PluginConfig, PluginResult

logger = get_logger(__name__)


class ChannelProgramFilterPlugin(BasePlugin):
    """Plugin to filter channels with no available programs in the next X hours."""
    
    @property
    def name(self) -> str:
        return "channel_program_filter"
    
    @property
    def description(self) -> str:
        return "Filter out channels if all programs are filtered within the next X hours"
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    @property
    def supported_tables(self) -> List[str]:
        return ["m3u_channels", "epg_channels"]
    
    def get_default_parameters(self) -> Dict[str, Any]:
        """Get default parameters for this plugin."""
        return {
            "hours_ahead": 24,  # Look ahead 24 hours by default
            "min_programs_required": 1,  # Require at least 1 unfiltered program
            "check_current_programs": True,  # Include currently running programs
            "skip_if_no_epg": True  # Skip filtering if no EPG data exists for channel
        }
    
    def get_parameter_schema(self) -> Dict[str, Any]:
        """Get JSON schema for plugin parameters."""
        return {
            "type": "object",
            "properties": {
                "hours_ahead": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 168,  # Max 1 week
                    "description": "Number of hours ahead to check for programs"
                },
                "min_programs_required": {
                    "type": "integer",
                    "minimum": 0,
                    "description": "Minimum number of unfiltered programs required"
                },
                "check_current_programs": {
                    "type": "boolean",
                    "description": "Include currently running programs in the check"
                },
                "skip_if_no_epg": {
                    "type": "boolean",
                    "description": "Skip filtering if no EPG data exists for the channel"
                }
            },
            "required": ["hours_ahead", "min_programs_required"],
            "additionalProperties": False
        }
    
    def validate_config(self) -> tuple[bool, List[str]]:
        """Validate plugin configuration."""
        errors = []
        
        # Check required parameters
        if "hours_ahead" not in self.parameters:
            errors.append("Missing required parameter: hours_ahead")
        elif not isinstance(self.parameters["hours_ahead"], int) or self.parameters["hours_ahead"] < 1:
            errors.append("hours_ahead must be a positive integer")
        elif self.parameters["hours_ahead"] > 168:
            errors.append("hours_ahead cannot exceed 168 hours (1 week)")
        
        if "min_programs_required" not in self.parameters:
            errors.append("Missing required parameter: min_programs_required")
        elif not isinstance(self.parameters["min_programs_required"], int) or self.parameters["min_programs_required"] < 0:
            errors.append("min_programs_required must be a non-negative integer")
        
        # Check optional parameters
        if "check_current_programs" in self.parameters and not isinstance(self.parameters["check_current_programs"], bool):
            errors.append("check_current_programs must be a boolean")
        
        if "skip_if_no_epg" in self.parameters and not isinstance(self.parameters["skip_if_no_epg"], bool):
            errors.append("skip_if_no_epg must be a boolean")
        
        return len(errors) == 0, errors
    
    def apply(
        self,
        record: Union[M3uChannel, EpgChannel, Program],
        table_name: str,
        source_name: str,
        context: Dict[str, Any] = None
    ) -> PluginResult:
        """Apply channel program filter logic to a channel record."""
        if table_name == "programs":
            # This plugin doesn't filter programs directly
            return PluginResult(passed=True, reason="Plugin does not filter programs")
        
        # Get database session from context
        if not context or "db_session" not in context:
            logger.warning("No database session provided in context, cannot check programs")
            return PluginResult(passed=True, reason="No database session available")
        
        db_session: Session = context["db_session"]
        
        # Get plugin parameters
        hours_ahead = self.parameters.get("hours_ahead", 24)
        min_programs_required = self.parameters.get("min_programs_required", 1)
        check_current_programs = self.parameters.get("check_current_programs", True)
        skip_if_no_epg = self.parameters.get("skip_if_no_epg", True)
        
        # Determine channel ID based on record type
        if isinstance(record, M3uChannel):
            channel_id = record.tvg_id
        elif isinstance(record, EpgChannel):
            channel_id = record.channel_id
        else:
            return PluginResult(passed=True, reason="Unsupported record type")
        
        if not channel_id:
            logger.debug(f"Channel has no ID, skipping program check")
            return PluginResult(passed=True, reason="Channel has no ID")
        
        try:
            # Calculate time window
            now = datetime.utcnow()
            end_time = now + timedelta(hours=hours_ahead)
            start_time = now if not check_current_programs else now - timedelta(hours=1)
            
            # Count unfiltered programs for this channel in the time window
            unfiltered_count = self._count_unfiltered_programs(
                db_session, source_name, channel_id, start_time, end_time
            )
            
            # Check if channel has any EPG data
            total_programs = self._count_total_programs(
                db_session, source_name, channel_id, start_time, end_time
            )
            
            # If no EPG data exists and skip_if_no_epg is True, pass the channel
            if total_programs == 0 and skip_if_no_epg:
                return PluginResult(
                    passed=True,
                    reason="No EPG data available for channel",
                    metadata={
                        "channel_id": channel_id,
                        "total_programs": total_programs,
                        "unfiltered_programs": unfiltered_count,
                        "time_window_hours": hours_ahead
                    }
                )
            
            # Check if channel meets minimum program requirements
            if unfiltered_count >= min_programs_required:
                return PluginResult(
                    passed=True,
                    reason=f"Channel has {unfiltered_count} unfiltered programs (>= {min_programs_required})",
                    metadata={
                        "channel_id": channel_id,
                        "total_programs": total_programs,
                        "unfiltered_programs": unfiltered_count,
                        "time_window_hours": hours_ahead
                    }
                )
            else:
                return PluginResult(
                    passed=False,
                    reason=f"Channel has only {unfiltered_count} unfiltered programs (< {min_programs_required}) in next {hours_ahead} hours",
                    metadata={
                        "channel_id": channel_id,
                        "total_programs": total_programs,
                        "unfiltered_programs": unfiltered_count,
                        "time_window_hours": hours_ahead
                    }
                )
        
        except Exception as e:
            logger.error(f"Error checking programs for channel {channel_id}: {e}")
            return PluginResult(
                passed=True,
                reason=f"Error checking programs: {str(e)}",
                metadata={"error": str(e)}
            )
    
    def _count_unfiltered_programs(
        self,
        db_session: Session,
        source_name: str,
        channel_id: str,
        start_time: datetime,
        end_time: datetime
    ) -> int:
        """Count unfiltered programs for a channel in the given time window."""
        try:
            # Query programs that are not filtered (filter_reason is NULL or 'Passed')
            query = text("""
                SELECT COUNT(*) as count
                FROM programs 
                WHERE source = :source_name 
                AND channel_id = :channel_id
                AND start_time >= :start_time 
                AND start_time <= :end_time
                AND (filter_reason IS NULL OR filter_reason = 'Passed')
            """)
            
            result = db_session.execute(query, {
                "source_name": source_name,
                "channel_id": channel_id,
                "start_time": start_time,
                "end_time": end_time
            }).fetchone()
            
            return result.count if result else 0
        
        except Exception as e:
            logger.error(f"Error counting unfiltered programs: {e}")
            return 0
    
    def _count_total_programs(
        self,
        db_session: Session,
        source_name: str,
        channel_id: str,
        start_time: datetime,
        end_time: datetime
    ) -> int:
        """Count total programs for a channel in the given time window."""
        try:
            query = text("""
                SELECT COUNT(*) as count
                FROM programs 
                WHERE source = :source_name 
                AND channel_id = :channel_id
                AND start_time >= :start_time 
                AND start_time <= :end_time
            """)
            
            result = db_session.execute(query, {
                "source_name": source_name,
                "channel_id": channel_id,
                "start_time": start_time,
                "end_time": end_time
            }).fetchone()
            
            return result.count if result else 0
        
        except Exception as e:
            logger.error(f"Error counting total programs: {e}")
            return 0
