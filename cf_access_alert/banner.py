"""Startup banner — ASCII art logo and version info."""

VERSION = "2.2.1"

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
    print(f"  Cloudflare Access login alert monitor")
    print()
    print(f"  Copyright (C) 2026 Shaq Shaq — https://github.com/jpar99")
    print(f"  License: GNU GPL v3 — https://www.gnu.org/licenses/gpl-3.0.html")
    print()