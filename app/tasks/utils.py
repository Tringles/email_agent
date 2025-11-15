"""Utility functions for email processing."""

import re
import base64
import quopri
from typing import Optional


def decode_encoded_words(text: Optional[str]) -> str:
    """
    Decode RFC 2047 encoded words (e.g., =?UTF-8?B?...?= or =?UTF-8?Q?...?=).
    
    Args:
        text: Text that may contain encoded words
        
    Returns:
        Decoded text
    """
    if not text:
        return ""
    
    # Pattern to match encoded words: =?charset?encoding?encoded_text?=
    # Example: =?UTF-8?B?64Sk7J2067KEIOyLnOumrOymiA==?=
    encoded_word_regex = r'=\?([^?]+)\?([BQ])\?([^?]+)\?='
    
    def decode_match(match):
        charset = match.group(1)
        encoding = match.group(2).upper()
        encoded_text = match.group(3)
        
        try:
            if encoding == 'B':
                # Base64 encoding
                byte_string = base64.b64decode(encoded_text)
            elif encoding == 'Q':
                # Quoted-printable encoding
                byte_string = quopri.decodestring(encoded_text)
            else:
                return match.group(0)  # Return original if unknown encoding
            
            return byte_string.decode(charset, errors='ignore')
        except Exception:
            # If decoding fails, return original
            return match.group(0)
    
    # Replace all encoded words in the text
    decoded_text = re.sub(encoded_word_regex, decode_match, text, flags=re.IGNORECASE)
    
    return decoded_text

