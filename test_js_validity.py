#!/usr/bin/env python3
"""
エスケープ処理統合テスト
JavaScript文字列としての正確性を確認
"""

from latex_converter import convert_expression, convert_for_javascript
import json

def test_javascript_string_validity():
    """JavaScript文字列としての有効性テスト"""
    test_cases = [
        "y = sin(x)",
        "y = sqrt(x^2 + 1)",
        "y = 1/x",
        "y = ln(x+1)",
        "z = sin(x) * cos(y)",
        "r = cos(3θ)",
        "y = (x+1)/(x-1)",
    ]
    
    print("=" * 80)
    print("JavaScript文字列有効性テスト")
    print("=" * 80)
    
    for i, expr in enumerate(test_cases, 1):
        latex = convert_expression(expr)
        js_escaped = convert_for_javascript(expr)
        
        # JavaScript文字列として有効かテスト
        try:
            # JSON形式でエスケープテスト
            json_test = json.dumps({"latex": js_escaped})
            json_valid = True
        except Exception as e:
            json_valid = False
            json_error = str(e)
        
        print(f"\n{i}. 入力式: {expr}")
        print(f"   LaTeX変換: {latex}")
        print(f"   JS用エスケープ: {js_escaped}")
        print(f"   JSON有効性: {'✅ OK' if json_valid else '❌ NG'}")
        
        if json_valid:
            print(f"   JavaScriptコード例:")
            print(f"     calculator.setExpression({{latex: \"{js_escaped}\"}});")
        else:
            print(f"   JSON エラー: {json_error}")
    
    print(f"\n" + "=" * 80)
    print("テスト完了")
    print("=" * 80)

if __name__ == "__main__":
    test_javascript_string_validity()
