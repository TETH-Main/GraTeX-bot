#!/usr/bin/env python3
"""
不等式変換テスト
"""

import json
from latex_converter import convert_expression

def test_inequality_conversion():
    """不等式変換のテスト"""
    
    test_cases = [
        # 基本的な不等式
        ("x > 5", "x \\gt 5"),
        ("x < 3", "x \\lt 3"),
        ("x >= 2", "x \\ge 2"),
        ("x <= 10", "x \\le 10"),
        
        # 複合的な不等式
        ("y <= sin(x)", "y \\le \\sin\\left(x\\right)"),
        ("x^2 >= 4", "x^2 \\ge 4"),
        ("sqrt(x) > 0", "\\sqrt{x} \\gt 0"),
        ("log(x) < 1", "\\log\\left(x\\right) \\lt 1"),
        
        # 連続不等式
        ("0 <= x <= 1", "0 \\le x \\le 1"),
        ("1 < y < 5", "1 \\lt y \\lt 5"),
        
        # 分数を含む不等式
        ("x/2 > 3", "\\frac{x}{2} \\gt 3"),
        ("1/x <= 5", "\\frac{1}{x} \\le 5"),
    ]
    
    print("=== 不等式変換テスト ===")
    
    for i, (input_expr, expected) in enumerate(test_cases, 1):
        result = convert_expression(input_expr)
        
        print(f"\nテスト {i}:")
        print(f"入力: {input_expr}")
        print(f"期待: {expected}")
        print(f"結果: {result}")
        
        if result == expected:
            print("✓ 成功")
        else:
            print("✗ 失敗")
        
        # JavaScript文字列として安全かチェック
        js_safe = json.dumps(result)
        print(f"JS安全: {js_safe}")

def test_inequality_with_javascript():
    """不等式のJavaScript統合テスト"""
    print("\n=== JavaScript統合テスト（不等式） ===")
    
    test_inequalities = [
        "y <= sin(x)",
        "x^2 >= 4", 
        "0 < x < 1",
        "sqrt(x) > log(x)"
    ]
    
    for expr in test_inequalities:
        latex_result = convert_expression(expr)
        js_safe = json.dumps(latex_result)
        
        js_code = f"""
        calculator.setExpression({{latex: {js_safe}}});
        console.log("不等式設定:", {js_safe});
        """
        
        print(f"\n入力: {expr}")
        print(f"LaTeX: {latex_result}")
        print(f"JS統合例:")
        print(js_code.strip())

if __name__ == "__main__":
    test_inequality_conversion()
    test_inequality_with_javascript()
