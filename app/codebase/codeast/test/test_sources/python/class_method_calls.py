class Calculator:
    def add(self, a: int, b: int) -> int:
        return a + b
    
    def multiply(self, a: int, b: int) -> int:
        return a * b
    
    def calculate(self, a: int, b: int) -> int:
        sum_result = self.add(a, b)
        product = self.multiply(a, b)
        return sum_result + product

