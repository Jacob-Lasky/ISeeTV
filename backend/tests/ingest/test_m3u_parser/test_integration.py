"""Integration tests for M3U parser following atomic design principles.

This module focuses on testing complex M3U parsing scenarios and workflows.
Each test validates end-to-end functionality with realistic data.
"""

import pytest

from ingest.m3u_parser import parse_m3u


class TestIntegrationScenarios:
    """Integration tests for complex M3U parsing scenarios."""

    @pytest.fixture
    def sample_m3u_content(self):
        """Fixture providing sample M3U content for integration tests."""
        return """#EXTM3U
#EXT-X-SESSION-DATA:DATA-ID="com.example.session"
#EXTINF:-1 tvg-id="cnn.us" tvg-name="CNN" tvg-logo="http://example.com/cnn.png" group-title="News",CNN
http://example.com/cnn/stream.m3u8
#EXTINF:-1 tvg-id="espn.us" tvg-name="ESPN" tvg-logo="http://example.com/espn.png" group-title="Sports",ESPN
http://example.com/espn/stream
#EXTINF:-1 tvg-id="movie1" tvg-name="Movie Channel" group-title="Movies",Movie Channel
http://example.com/movies/movie.mp4
#EXTINF:-1,Channel Without Attributes
http://example.com/basic/stream
"""

    def test_complete_m3u_parsing_workflow(self, tmp_path, sample_m3u_content):
        """Test complete M3U parsing workflow with various channel types."""
        m3u_file = tmp_path / "sample.m3u"
        m3u_file.write_text(sample_m3u_content)

        channels = parse_m3u(str(m3u_file), source="integration_test")

        assert len(channels) == 4

        # Test CNN (complete attributes)
        cnn = next(ch for ch in channels if ch.tvg_id == "cnn.us")
        assert cnn.name == "CNN"
        assert cnn.logo_url == "http://example.com/cnn.png"
        assert cnn.group == "News"
        assert cnn.stream_mode == "live"
        assert cnn.source == "integration_test"

        # Test Movie Channel (on-demand detection)
        movie = next(ch for ch in channels if ch.tvg_id == "movie1")
        assert movie.stream_mode == "on_demand"
        assert movie.name == "Movie Channel"
        assert movie.group == "Movies"

        # Test channel without attributes
        basic = next(
            ch for ch in channels if ch.name == "Channel Without Attributes"
        )
        assert basic.tvg_id == "Channel Without Attributes"  # Uses name as fallback
        assert basic.logo_url is None
        assert basic.group is None

        # Test ESPN (standard live stream)
        espn = next(ch for ch in channels if ch.tvg_id == "espn.us")
        assert espn.name == "ESPN"
        assert espn.group == "Sports"
        assert espn.stream_mode == "live"

    def test_mixed_content_types_integration(self, tmp_path):
        """Test parsing M3U with mixed live streams and on-demand content."""
        content = """#EXTM3U
#EXTINF:-1 tvg-id="live1" group-title="Live",Live Stream 1
http://live.example.com/stream1
#EXTINF:-1 tvg-id="vod1" group-title="Movies",Movie File
http://vod.example.com/movie.mp4
#EXTINF:-1 tvg-id="live2" group-title="Live",Live Stream 2
http://live.example.com/stream2.m3u8
#EXTINF:-1 tvg-id="vod2" group-title="Series",TV Show
http://vod.example.com/show.mkv
"""
        m3u_file = tmp_path / "mixed.m3u"
        m3u_file.write_text(content)

        channels = parse_m3u(str(m3u_file), source="mixed_test")

        assert len(channels) == 4

        # Verify live streams
        live_channels = [ch for ch in channels if ch.stream_mode == "live"]
        assert len(live_channels) == 2
        
        # Verify on-demand content
        vod_channels = [ch for ch in channels if ch.stream_mode == "on_demand"]
        assert len(vod_channels) == 2

        # Check specific channels
        movie = next(ch for ch in channels if ch.tvg_id == "vod1")
        assert movie.stream_mode == "on_demand"
        assert movie.stream_url.endswith(".mp4")

        tv_show = next(ch for ch in channels if ch.tvg_id == "vod2")
        assert tv_show.stream_mode == "on_demand"
        assert tv_show.stream_url.endswith(".mkv")

    def test_large_playlist_integration(self, tmp_path):
        """Test parsing large M3U playlist with many channels."""
        # Generate content for 100 channels
        lines = ["#EXTM3U"]
        for i in range(100):
            group = "News" if i % 3 == 0 else "Sports" if i % 3 == 1 else "Entertainment"
            lines.append(f'#EXTINF:-1 tvg-id="ch{i}" tvg-name="Channel {i}" group-title="{group}",Channel {i}')
            lines.append(f"http://example.com/stream{i}")
        
        content = "\n".join(lines)
        m3u_file = tmp_path / "large.m3u"
        m3u_file.write_text(content)

        channels = parse_m3u(str(m3u_file), source="large_test")

        assert len(channels) == 100

        # Verify distribution across groups
        news_channels = [ch for ch in channels if ch.group == "News"]
        sports_channels = [ch for ch in channels if ch.group == "Sports"]
        entertainment_channels = [ch for ch in channels if ch.group == "Entertainment"]

        assert len(news_channels) == 34  # 0, 3, 6, ..., 99 (34 total)
        assert len(sports_channels) == 33  # 1, 4, 7, ..., 97 (33 total)
        assert len(entertainment_channels) == 33  # 2, 5, 8, ..., 98 (33 total)

        # Verify first and last channels
        first_channel = next(ch for ch in channels if ch.tvg_id == "ch0")
        assert first_channel.name == "Channel 0"
        assert first_channel.group == "News"

        last_channel = next(ch for ch in channels if ch.tvg_id == "ch99")
        assert last_channel.name == "Channel 99"
        assert last_channel.group == "News"

    def test_malformed_content_integration(self, tmp_path):
        """Test parsing M3U with various malformed entries."""
        content = """#EXTM3U
#EXTINF:-1 tvg-id="valid1",Valid Channel 1
http://example.com/valid1

# Comment line
#EXTINF:-1 tvg-id="orphan",Orphaned Channel
# Missing URL for orphaned channel

#EXTINF:-1 tvg-id="valid2",Valid Channel 2
http://example.com/valid2

Invalid line without EXTINF
http://example.com/orphaned_url

#EXTINF:-1 tvg-id="valid3",Valid Channel 3
http://example.com/valid3
"""
        m3u_file = tmp_path / "malformed.m3u"
        m3u_file.write_text(content)

        channels = parse_m3u(str(m3u_file), source="malformed_test")

        # Should only parse valid channel pairs
        assert len(channels) == 3
        
        valid_ids = {ch.tvg_id for ch in channels}
        assert valid_ids == {"valid1", "valid2", "valid3"}

        # Verify all channels are properly formed
        for channel in channels:
            assert channel.tvg_id.startswith("valid")
            assert channel.stream_url.startswith("http://example.com/valid")
            assert channel.source == "malformed_test"

    def test_unicode_content_integration(self, tmp_path):
        """Test parsing M3U with Unicode characters in channel names and metadata."""
        content = """#EXTM3U
#EXTINF:-1 tvg-id="fr1" tvg-name="Chaîne française" group-title="Français",Chaîne française
http://example.com/french/stream
#EXTINF:-1 tvg-id="ru1" tvg-name="Русский канал" group-title="Русский",Русский канал
http://example.com/russian/stream
#EXTINF:-1 tvg-id="jp1" tvg-name="日本のチャンネル" group-title="日本語",日本のチャンネル
http://example.com/japanese/stream
#EXTINF:-1 tvg-id="emoji1" tvg-name="Channel 🎬📺" group-title="Entertainment 🎭",Channel 🎬📺
http://example.com/emoji/stream
"""
        m3u_file = tmp_path / "unicode.m3u"
        m3u_file.write_text(content, encoding="utf-8")

        channels = parse_m3u(str(m3u_file), source="unicode_test")

        assert len(channels) == 4

        # Test French channel
        french = next(ch for ch in channels if ch.tvg_id == "fr1")
        assert french.name == "Chaîne française"
        assert french.group == "Français"

        # Test Russian channel
        russian = next(ch for ch in channels if ch.tvg_id == "ru1")
        assert russian.name == "Русский канал"
        assert russian.group == "Русский"

        # Test Japanese channel
        japanese = next(ch for ch in channels if ch.tvg_id == "jp1")
        assert japanese.name == "日本のチャンネル"
        assert japanese.group == "日本語"

        # Test emoji channel
        emoji = next(ch for ch in channels if ch.tvg_id == "emoji1")
        assert emoji.name == "Channel 🎬📺"
        assert emoji.group == "Entertainment 🎭"

    def test_real_world_iptv_playlist_structure(self, tmp_path):
        """Test parsing realistic IPTV playlist structure."""
        content = """#EXTM3U x-tvg-url="http://example.com/epg.xml"
#EXT-X-SESSION-DATA:DATA-ID="com.provider.session"
#EXT-X-VERSION:3

#EXTINF:-1 tvg-id="BBC1.uk" tvg-name="BBC One" tvg-logo="http://provider.com/logos/bbc1.png" group-title="UK | Entertainment" timeshift="0",BBC One HD
http://provider.com/live/bbc1/index.m3u8

#EXTINF:-1 tvg-id="CNN.us" tvg-name="CNN International" tvg-logo="http://provider.com/logos/cnn.png" group-title="USA | News" timeshift="3",CNN International
http://provider.com/live/cnn/playlist.m3u8

#EXTINF:-1 tvg-id="MOVIE1" tvg-name="Movie: The Matrix" tvg-logo="http://provider.com/movies/matrix.jpg" group-title="Movies | Sci-Fi",The Matrix (1999)
http://provider.com/vod/movies/matrix.mp4

#EXTINF:-1 tvg-id="SPORT1.espn" tvg-name="ESPN" tvg-logo="http://provider.com/logos/espn.png" group-title="USA | Sports",ESPN HD
http://provider.com/live/espn/stream

#EXT-X-DISCONTINUITY
#EXTINF:-1 tvg-id="LOCAL.news" tvg-name="Local News" group-title="Local",Local News Channel
http://local.provider.com/news/live
"""
        m3u_file = tmp_path / "realistic.m3u"
        m3u_file.write_text(content)

        channels = parse_m3u(str(m3u_file), source="iptv_provider")

        assert len(channels) == 5

        # Test BBC One (live with complex group)
        bbc = next(ch for ch in channels if ch.tvg_id == "BBC1.uk")
        assert bbc.name == "BBC One"
        assert bbc.group == "UK | Entertainment"
        assert bbc.stream_mode == "live"
        assert bbc.logo_url == "http://provider.com/logos/bbc1.png"

        # Test Movie (on-demand)
        movie = next(ch for ch in channels if ch.tvg_id == "MOVIE1")
        assert movie.name == "Movie: The Matrix"
        assert movie.group == "Movies | Sci-Fi"
        assert movie.stream_mode == "on_demand"
        assert movie.stream_url.endswith(".mp4")

        # Test Local channel (minimal attributes)
        local = next(ch for ch in channels if ch.tvg_id == "LOCAL.news")
        assert local.name == "Local News"
        assert local.group == "Local"
        assert local.logo_url is None

        # Verify all channels have correct source
        for channel in channels:
            assert channel.source == "iptv_provider"
