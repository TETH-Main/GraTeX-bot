#!/usr/bin/env python3
"""
JavaScript統合テスト：JSON.dumpsを使ったエスケープのテスト
"""

import json
from latex_converter import convert_expression

def test_json_dumps_escaping():
    """json.dumps()を使ったJavaScriptエスケープのテスト"""
    
    test_cases = [
        "y=sin(x)",
        "y=cos(x)^2",
        "y=sqrt(x)",
        "y=x^2/2",
        "y=|x|",
        "y=log(x)"
    ]
    
    print("=== JavaScript統合テスト ===")
    
    for expr in test_cases:
        # LaTeX変換
        latex_expr = convert_expression(expr)
        
        # JSON.dumpsでJavaScript文字列として安全にエスケープ
        js_safe_expr = json.dumps(latex_expr)
        
        # f-stringでJavaScriptコードに埋め込む例
        js_code = f"""
        calculator.setExpression({{latex: {js_safe_expr}}});
        console.log("設定した式:", {js_safe_expr});
        """
        
        print(f"\n入力: {expr}")
        print(f"LaTeX: {latex_expr}")
        print(f"JS文字列: {js_safe_expr}")
        print(f"生成されるJSコード:")
        print(js_code.strip())
        
        # JavaScriptとして有効かチェック（簡易）
        try:
            # JSON.dumpsの結果が正しくエスケープされているか
            parsed = json.loads(js_safe_expr)
            assert parsed == latex_expr
            print("✓ JSON.dumps エスケープ成功")
        except (json.JSONDecodeError, AssertionError) as e:
            print(f"✗ JSON.dumps エスケープ失敗: {e}")

if __name__ == "__main__":
    test_json_dumps_escaping()
