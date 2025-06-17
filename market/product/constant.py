from enum import Enum # Import Enum

class ProductType(Enum):
    """
    Represents the type of financial product.
    """
    STOCK = "STOCK" 
    ETF = "ETF"  
    ALL = "ALL"

