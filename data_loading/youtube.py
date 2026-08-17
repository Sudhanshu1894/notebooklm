"""
YouTube Transcript Extractor.
"""

import re
from typing import List, Dict, Any
from youtube_transcript_api import YouTubeTranscriptApi
import uuid

class YouTubeExtractor:
    """
    Detects YouTube URLs and extracts their transcripts into context chunks.
    """
    
    # Regex to match youtube.com and youtu.be URLs
    YT_REGEX = re.compile(
        r'(https?://)?(www\.)?'
        r'(youtube|youtu|youtube-nocookie)\.(com|be)/'
        r'(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})'
    )
    
    def extract_urls(self, query: str) -> List[str]:
        """Finds all video IDs in a text query."""
        matches = self.YT_REGEX.findall(query)
        video_ids = [m[5] for m in matches if len(m) >= 6 and m[5]]
        return list(set(video_ids))
        
    def get_transcript_chunks(self, video_id: str) -> List[Dict[str, Any]]:
        """Fetches the transcript and formats it into context chunks."""
        chunks = []
        try:
            transcript = YouTubeTranscriptApi().fetch(video_id)
            
            # Combine transcript pieces into larger chunks (~500 chars)
            current_chunk_text = ""
            start_time = 0.0
            
            for item in transcript:
                text = item.text.replace('\n', ' ')
                if not current_chunk_text:
                    start_time = item.start
                    
                current_chunk_text += text + " "
                
                # If chunk is large enough, save it
                if len(current_chunk_text) >= 500:
                    chunks.append(self._create_chunk(video_id, current_chunk_text, start_time))
                    current_chunk_text = ""
            
            # Add remaining text
            if current_chunk_text:
                chunks.append(self._create_chunk(video_id, current_chunk_text, start_time))
                
        except Exception as e:
            print(f"[YouTubeExtractor] Error fetching transcript for {video_id}: {e}")
            
        return chunks

    def _create_chunk(self, video_id: str, text: str, start_time: float) -> Dict[str, Any]:
        """Helper to format a single chunk."""
        # Convert seconds to mm:ss
        mins = int(start_time // 60)
        secs = int(start_time % 60)
        timestamp = f"{mins}:{secs:02d}"
        
        return {
            "chunk_id": f"yt_{uuid.uuid4().hex[:8]}",
            "text": text.strip(),
            "metadata": {
                "doc_id": f"https://youtube.com/watch?v={video_id}",
                "page_number": f"[{timestamp}]",
                "section_header": "YouTube Transcript",
                "source": "youtube"
            }
        }
