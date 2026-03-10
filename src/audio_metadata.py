"""
Audio Metadata Embedder

Embeds metadata (title, date, episode number, description, source links)
into MP3 and WAV audio files using ID3 tags.
"""

import logging
from pathlib import Path
from typing import List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

try:
    from mutagen.id3 import ID3, TIT2, TDRC, TCON, COMM, TXXX
    MUTAGEN_AVAILABLE = True
except ImportError:
    MUTAGEN_AVAILABLE = False
    logger.warning(
        "mutagen library not installed. Audio metadata embedding will be disabled. "
        "Install with: pip install mutagen"
    )


class AudioMetadataEmbedder:
    """
    Embeds metadata into MP3 and WAV audio files.

    Uses ID3 tags for MP3 and similar metadata structures for WAV.
    """

    @staticmethod
    def embed_mp3_metadata(
        file_path: Path,
        title: str,
        episode_number: Optional[str] = None,
        date: Optional[str] = None,
        description: Optional[str] = None,
        source_links: Optional[List[str]] = None,
    ) -> bool:
        """
        Embed metadata into MP3 file using ID3 tags.

        Args:
            file_path: Path to MP3 file
            title: Episode title
            episode_number: Episode number or ID
            date: Publication date (ISO format)
            description: Episode description
            source_links: List of source URLs

        Returns:
            True if successful, False otherwise
        """
        if not MUTAGEN_AVAILABLE:
            logger.warning("mutagen not available, skipping MP3 metadata")
            return False

        if not file_path.exists():
            logger.error(f"MP3 file not found: {file_path}")
            return False

        try:
            # Load or create ID3 tags
            audio = ID3(str(file_path))
        except Exception:
            # Create new ID3 tags if none exist
            try:
                audio = ID3()
            except Exception as e:
                logger.error(f"Failed to create ID3 tags for {file_path}: {e}")
                return False

        try:
            # Set title
            audio["TIT2"] = TIT2(encoding=3, text=[title])

            # Set date
            if date:
                audio["TDRC"] = TDRC(encoding=3, text=[date])
            else:
                audio["TDRC"] = TDRC(encoding=3, text=[datetime.utcnow().isoformat()])

            # Set episode number as content group
            if episode_number:
                audio["TCON"] = TCON(encoding=3, text=[f"Episode: {episode_number}"])

            # Set description/comment
            if description:
                audio["COMM"] = COMM(
                    encoding=3,
                    lang="eng",
                    desc="",
                    text=[description]
                )

            # Add source links as user-defined text frames
            if source_links:
                links_text = "\n".join(source_links)
                audio["TXXX:SOURCE_LINKS"] = TXXX(
                    encoding=3,
                    desc="SOURCE_LINKS",
                    text=[links_text]
                )
                # Also add as simple comment if description is empty
                if not description:
                    audio["COMM"] = COMM(
                        encoding=3,
                        lang="eng",
                        desc="Sources",
                        text=[links_text[:200]]  # Limit length
                    )

            # Save metadata to file
            audio.save(str(file_path), v2_version=4)
            logger.info(f"Embedded metadata in MP3: {file_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to embed metadata in {file_path}: {e}")
            return False

    @staticmethod
    def embed_wav_metadata(
        file_path: Path,
        title: str,
        episode_number: Optional[str] = None,
        date: Optional[str] = None,
        description: Optional[str] = None,
        source_links: Optional[List[str]] = None,
    ) -> bool:
        """
        Embed metadata into WAV file.

        WAV files use INFO chunks. This implementation focuses on
        MP3 ID3 compatibility when possible.

        Args:
            file_path: Path to WAV file
            title: Episode title
            episode_number: Episode number or ID
            date: Publication date
            description: Episode description
            source_links: List of source URLs

        Returns:
            True if successful (or skipped), False if critical error
        """
        # WAV metadata support is limited
        # For now, we'll log the attempt and consider it a non-blocking operation
        logger.info(
            f"WAV metadata embedding requested for {file_path}. "
            f"(Full WAV metadata support requires extended libraries)"
        )

        # Attempt to embed using mutagen's generic approach if available
        if not MUTAGEN_AVAILABLE:
            logger.debug("mutagen not available for WAV metadata")
            return True  # Non-blocking

        try:
            from mutagen.wave import WAVE
            from mutagen.id3 import ID3

            if not file_path.exists():
                logger.error(f"WAV file not found: {file_path}")
                return False

            # Try to load or create ID3 tags in WAV
            try:
                audio = ID3(str(file_path))
            except Exception:
                audio = ID3()

            # Set metadata (same as MP3)
            audio["TIT2"] = TIT2(encoding=3, text=[title])

            if date:
                audio["TDRC"] = TDRC(encoding=3, text=[date])
            if episode_number:
                audio["TCON"] = TCON(encoding=3, text=[f"Episode: {episode_number}"])
            if description:
                audio["COMM"] = COMM(
                    encoding=3,
                    lang="eng",
                    desc="",
                    text=[description]
                )

            # Save to WAV file
            audio.save(str(file_path), v2_version=4)
            logger.info(f"Embedded metadata in WAV: {file_path}")
            return True

        except ImportError:
            logger.debug("mutagen.wave not available")
            return True  # Non-blocking
        except Exception as e:
            logger.warning(f"WAV metadata embedding failed (non-blocking): {e}")
            return True  # WAV metadata is non-critical

    @staticmethod
    def embed_audio_metadata(
        file_path: Path,
        title: str,
        episode_number: Optional[str] = None,
        date: Optional[str] = None,
        description: Optional[str] = None,
        source_links: Optional[List[str]] = None,
    ) -> bool:
        """
        Embed metadata into audio file (MP3 or WAV).

        Automatically detects file format and uses appropriate method.

        Args:
            file_path: Path to audio file
            title: Episode title
            episode_number: Episode number
            date: Publication date
            description: Episode description
            source_links: List of source URLs

        Returns:
            True if successful, False otherwise
        """
        file_path = Path(file_path)
        suffix = file_path.suffix.lower()

        if suffix == ".mp3":
            return AudioMetadataEmbedder.embed_mp3_metadata(
                file_path=file_path,
                title=title,
                episode_number=episode_number,
                date=date,
                description=description,
                source_links=source_links
            )
        elif suffix == ".wav":
            return AudioMetadataEmbedder.embed_wav_metadata(
                file_path=file_path,
                title=title,
                episode_number=episode_number,
                date=date,
                description=description,
                source_links=source_links
            )
        else:
            logger.warning(f"Unsupported audio format: {suffix}")
            return False

    @staticmethod
    def validate_metadata(file_path: Path) -> bool:
        """
        Validate that metadata was successfully embedded.

        Args:
            file_path: Path to audio file

        Returns:
            True if metadata is present, False otherwise
        """
        if not MUTAGEN_AVAILABLE or not file_path.exists():
            return False

        try:
            from mutagen.easyid3 import EasyID3

            audio = EasyID3(str(file_path))
            # Check if any metadata exists
            return len(audio) > 0
        except Exception:
            return False
