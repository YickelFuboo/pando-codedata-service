from typing import List, Dict, Optional

def complex_function(
    items: List[str],
    config: Dict[str, int],
    callback: Optional[callable] = None
) -> Dict[str, List[str]]:
    return {"result": items}

