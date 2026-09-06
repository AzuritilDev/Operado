"""HTTP request headers related operations will be handled here"""
import random

def randomize_user_agent() -> str:
        discord_versions = [
            "69548",
            "69547",
            "69546",
            "69545"
        ]
        
        darwin_versions = [
            "24.3.0",
            "24.2.0",
            "24.1.0",
            "23.3.0"
        ]
        
        cfnetwork_versions = [
            "3826.400.110",
            "3826.400.100",
            "3826.300.110"
        ]
        
        version = random.choice(discord_versions)
        darwin = random.choice(darwin_versions)
        cfnet = random.choice(cfnetwork_versions)
        
        return f'Discord/{version} CFNetwork/{cfnet} Darwin/{darwin}'