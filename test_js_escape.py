#!/usr/bin/env python3
"""
JavaScript用エスケープテスト
"""

from latex_converter import convert_expression, convert_for_javascript

def test_javascript_escaping():
    """JavaScript用エスケープのテスト"""
    test_cases = [
        "y = sin(x)",
        "y = sqrt(x)",
        "y = ln(x)",
        "y = 1/x",
        "z = sin(x) * cos(y)",
        "r = cos(3θ)",
    ]
    
    print("=" * 80)
    print("JavaScript用エスケープテスト")
    print("=" * 80)
    
    for i, expr in enumerate(test_cases, 1):
        latex = convert_expression(expr)
        js_escaped = convert_for_javascript(expr)
        
        print(f"\n{i}. 入力: {expr}")
        print(f"   LaTeX: {latex}")
        print(f"   JS用:  {js_escaped}")
        print(f"   文字列表現: \"{js_escaped}\"")
        
        # JavaScriptコードとしての例
        js_code = f"calculator.setExpression({{latex: \"{js_escaped}\"}});"
        print(f"   JSコード例: {js_code}")
    
    print(f"\n" + "=" * 80)
    print("エスケープテスト完了")
    print("=" * 80)

if __name__ == "__main__":
    test_javascript_escaping()
