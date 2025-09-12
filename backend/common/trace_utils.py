"""Atomic tracing utilities for ISeeTV rules engine.

This module provides pure functions for building rule execution traces and filter reasons
following atomic design principles. Each function has a single responsibility and is
easily testable in isolation.
"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum

from common.log_utils import get_logger

logger = get_logger(__name__)


class TraceAction(Enum):
    """Enumeration of possible trace actions."""
    ENTERED = "entered"
    RULE_PASSED = "PASSED"
    RULE_CAUGHT = "CAUGHT"
    TERMINATED = "terminated"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"


@dataclass
class TraceStep:
    """Atomic representation of a single trace step."""
    action: TraceAction
    location: str
    rule_name: Optional[str] = None
    reason: Optional[str] = None
    
    def to_string(self) -> str:
        """Convert trace step to human-readable string."""
        if self.action == TraceAction.ENTERED:
            return f"entered: {self.location}"
        elif self.action in [TraceAction.RULE_PASSED, TraceAction.RULE_CAUGHT]:
            return f"rule:{self.rule_name} - {self.action.value}"
        elif self.action in [TraceAction.TERMINATED, TraceAction.ACCEPTED, TraceAction.REJECTED]:
            reason_part = f" - {self.reason}" if self.reason else ""
            return f"{self.action.value.lower()}{reason_part}"
        else:
            return f"{self.action.value}: {self.location}"


@dataclass
class RuleTrace:
    """Container for building rule execution traces."""
    steps: List[TraceStep] = field(default_factory=list)
    filter_reasons: Dict[str, bool] = field(default_factory=dict)
    accepted: Optional[bool] = None
    
    def add_step(self, action: TraceAction, location: str, rule_name: Optional[str] = None, reason: Optional[str] = None) -> None:
        """Add a step to the trace (atomic operation)."""
        step = TraceStep(action=action, location=location, rule_name=rule_name, reason=reason)
        self.steps.append(step)
        logger.debug(f"Added trace step: {step.to_string()}")
    
    def set_rule_result(self, rule_name: str, passed: bool) -> None:
        """Set the result of a rule evaluation (atomic operation)."""
        self.filter_reasons[rule_name] = passed
        logger.debug(f"Set rule result: {rule_name} = {passed}")
    
    def set_accepted(self, accepted: bool, reason: Optional[str] = None) -> None:
        """Set the final acceptance status (atomic operation)."""
        self.accepted = accepted
        action = TraceAction.ACCEPTED if accepted else TraceAction.REJECTED
        self.add_step(action, "final_decision", reason=reason)
        logger.debug(f"Set accepted: {accepted}, reason: {reason}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert trace to dictionary for database storage."""
        return {
            "_trace": [step.to_string() for step in self.steps],
            "filter_reasons": self.filter_reasons,
            "accepted": self.accepted
        }
    
    def to_trace_array(self) -> List[str]:
        """Get just the trace array for backward compatibility."""
        return [step.to_string() for step in self.steps]


def create_trace() -> RuleTrace:
    """Create a new empty trace (atomic factory function)."""
    return RuleTrace()


def trace_table_entry(trace: RuleTrace, table_name: str) -> None:
    """Record entry into a table for processing (atomic operation)."""
    trace.add_step(TraceAction.ENTERED, table_name)


def trace_rule_evaluation(trace: RuleTrace, rule_name: str, passed: bool, caught: bool = False) -> None:
    """Record the result of a rule evaluation (atomic operation)."""
    trace.set_rule_result(rule_name, passed)
    
    if caught:
        trace.add_step(TraceAction.RULE_CAUGHT, "rule_evaluation", rule_name=rule_name)
    else:
        trace.add_step(TraceAction.RULE_PASSED, "rule_evaluation", rule_name=rule_name)


def trace_termination(trace: RuleTrace, rule_name: str, reason: str) -> None:
    """Record termination at a specific rule (atomic operation)."""
    trace.add_step(TraceAction.TERMINATED, f"{rule_name}.caught", reason=reason)


def trace_final_decision(trace: RuleTrace, accepted: bool, reason: Optional[str] = None) -> None:
    """Record the final acceptance/rejection decision (atomic operation)."""
    trace.set_accepted(accepted, reason)


def merge_trace_into_record(record_dict: Dict[str, Any], trace: RuleTrace) -> Dict[str, Any]:
    """Merge trace data into a record dictionary (atomic operation)."""
    trace_data = trace.to_dict()
    record_dict.update(trace_data)
    return record_dict


def extract_trace_from_record(record_dict: Dict[str, Any]) -> Optional[RuleTrace]:
    """Extract trace data from a record dictionary (atomic operation)."""
    if "_trace" not in record_dict:
        return None
    
    trace = create_trace()
    
    # Reconstruct filter_reasons if present
    if "filter_reasons" in record_dict and record_dict["filter_reasons"]:
        trace.filter_reasons = record_dict["filter_reasons"]
    
    # Reconstruct accepted status if present
    if "accepted" in record_dict:
        trace.accepted = record_dict["accepted"]
    
    # Note: We don't reconstruct the steps from the trace array as that would be complex
    # and is primarily for display purposes
    
    return trace


def validate_trace_data(trace_data: Dict[str, Any]) -> bool:
    """Validate trace data structure (atomic validation function)."""
    try:
        # Check required fields
        if "_trace" not in trace_data:
            return False
        
        # Validate _trace is a list of strings
        if not isinstance(trace_data["_trace"], list):
            return False
        
        for step in trace_data["_trace"]:
            if not isinstance(step, str):
                return False
        
        # Validate filter_reasons if present
        if "filter_reasons" in trace_data:
            if trace_data["filter_reasons"] is not None:
                if not isinstance(trace_data["filter_reasons"], dict):
                    return False
                for rule_name, result in trace_data["filter_reasons"].items():
                    if not isinstance(rule_name, str) or not isinstance(result, bool):
                        return False
        
        # Validate accepted if present
        if "accepted" in trace_data:
            if trace_data["accepted"] is not None and not isinstance(trace_data["accepted"], bool):
                return False
        
        return True
    
    except Exception as e:
        logger.error(f"Error validating trace data: {e}")
        return False


def format_trace_for_display(trace_array: List[str]) -> str:
    """Format trace array for human-readable display (atomic formatting function)."""
    if not trace_array:
        return "No trace available"
    
    formatted_lines = []
    for i, step in enumerate(trace_array, 1):
        formatted_lines.append(f"{i:2d}. {step}")
    
    return "\n".join(formatted_lines)


def get_trace_summary(trace_data: Dict[str, Any]) -> Dict[str, Any]:
    """Get a summary of trace data for quick overview (atomic summary function)."""
    summary = {
        "total_steps": 0,
        "rules_evaluated": 0,
        "rules_passed": 0,
        "rules_caught": 0,
        "final_status": "unknown",
        "terminated_at": None
    }
    
    if "_trace" not in trace_data:
        return summary
    
    trace_array = trace_data["_trace"]
    summary["total_steps"] = len(trace_array)
    
    filter_reasons = trace_data.get("filter_reasons", {})
    if filter_reasons:
        summary["rules_evaluated"] = len(filter_reasons)
        summary["rules_passed"] = sum(1 for passed in filter_reasons.values() if passed)
        summary["rules_caught"] = sum(1 for passed in filter_reasons.values() if not passed)
    
    accepted = trace_data.get("accepted")
    if accepted is True:
        summary["final_status"] = "accepted"
    elif accepted is False:
        summary["final_status"] = "rejected"
    
    # Find termination point
    for step in trace_array:
        if "terminated at" in step:
            summary["terminated_at"] = step.split("terminated at ")[1].split(" - ")[0]
            break
    
    return summary
