"""Startup banner — ASCII art logo and version info.

VERSION resolution order:
1. CF_ACCESS_ALERT_VERSION environment variable (set in production images
   from the docker --build-arg, so the image is always stamped with the
   tag's version regardless of what the VERSION file says)
2. VERSION file at the repo root (used for local development and as a
   fallback inside images that didn't get a build-arg)
3. "0.0.0-dev" if neither is available (e.g. running from a clone with
   no VERSION file)
"""

import os
from pathlib import Path


def _resolve_version() -> str:
    env = os.environ.get("CF_ACCESS_ALERT_VERSION", "").strip()
    if env:
        return env

    # banner.py lives in cf_access_alert/, so the repo root is two parents up
    version_file = Path(__file__).resolve().parent.parent / "VERSION"
    try:
        text = version_file.read_text().strip()
        if text:
            return text
    except OSError:
        pass

    return "0.0.0-dev"


VERSION = _resolve_version()

BANNER = r"""
                                              
                      --                      
                    ------                    
                   ---------                  
               --- ------------               
        ---------- -------------------        
       ----------- --------------------       
       ----------- --------------------       
       ----------- --------------------       
       ----------- --------------------       
       ----------- ---------- ---------       
       ----------- ------------ -------       
       --------       ---------   -----       
       ----------   ------------ ------       
       ----------- ----------- --------       
        ---------- ---------- --------        
         --------- -------------------        
         --------- ------------------         
          -------- -----------------          
            ------ ---------------            
             ----- --------------             
               --- ------------               
                   ----------                 
                     ----                     
"""


def print_banner() -> None:
    """Print the startup banner to stdout (bypasses logging formatter)."""
    print(BANNER)
    print(f"  cf-access-alert v{VERSION}")
    print("  Cloudflare Access login alert monitor")
    print()
    print("  Copyright (C) 2026 Shaquille Oatmeal — https://github.com/jpar99")
    print("  License: GNU GPL v3 — https://www.gnu.org/licenses/gpl-3.0.html")
    print()
