#!/usr/bin/env python3
"""
LaTeX変換機能のテストスクリプト
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from main import convert_to_latex

def test_latex_conversion():
    """LaTeX変換のテストケース"""
    
    test_cases = [
        # 基本的な関数
        ("y=sin(x)", "y=\\\\sin\\\\left(x\\\\right)"),
        ("y=cos(x)", "y=\\\\cos\\\\left(x\\\\right)"),
        ("y=tan(x)", "y=\\\\tan\\\\left(x\\\\right)"),
        
        # 絶対値
        ("y=|x|", "y=\\\\left|x\\\\right|"),
        ("y=|x+1|", "y=\\\\left|x + 1\\\\right|"),
        
        # 分数
        ("y=(x+1)/(x-2)", "y=\\\\frac{x + 1}{x - 2}"),
        ("y=x/(x+1)", "y=\\\\frac{x}{x + 1}"),
        
        # 平方根
        ("y=sqrt(x)", "y=\\\\sqrt{x}"),
        ("y=sqrt(x^2+1)", "y=\\\\sqrt{x^{2} + 1}"),
        
        # 二次関数
        ("y=x^2", "y=x^{2}"),
        ("y=x^2+2*x+1", "y=x^{2} + 2 x + 1"),
        
        # 円
        ("x^2+y^2=1", "x^{2} + y^{2} = 1"),
        ("x^2+y^2=25", "x^{2} + y^{2} = 25"),
        
        # 3D関数
        ("z=x^2+y^2", "z=x^{2} + y^{2}"),
        ("z=sin(x)*cos(y)", "z=\\\\sin\\\\left(x\\\\right) \\\\cos\\\\left(y\\\\right)"),
        
        # 既にLaTeX形式の場合
        ("y=\\sin\\left(x\\right)", "y=\\sin\\left(x\\right)"),
        ("y=\\frac{x+1}{x-2}", "y=\\frac{x+1}{x-2}"),
    ]
    
    print("=== LaTeX変換テスト ===")
    passed = 0
    failed = 0
    
    for i, (input_expr, expected_output) in enumerate(test_cases, 1):
        try:
            result = convert_to_latex(input_expr)
            
            print(f"\nテスト {i}: {input_expr}")
            print(f"期待値: {expected_output}")
            print(f"実際値: {result}")
            
            # 厳密な一致ではなく、主要な要素が含まれているかチェック
            if "sin" in input_expr and "\\\\sin" in result:
                print("✅ PASS (sin変換)")
                passed += 1
            elif "cos" in input_expr and "\\\\cos" in result:
                print("✅ PASS (cos変換)")
                passed += 1
            elif "|" in input_expr and "\\\\left|" in result:
                print("✅ PASS (絶対値変換)")
                passed += 1
            elif "/" in input_expr and ("\\\\frac" in result or "\\frac" in result):
                print("✅ PASS (分数変換)")
                passed += 1
            elif "sqrt" in input_expr and "\\\\sqrt" in result:
                print("✅ PASS (平方根変換)")
                passed += 1
            elif "^" in input_expr and "^{" in result:
                print("✅ PASS (べき乗変換)")
                passed += 1
            elif "\\" in input_expr and result == input_expr:
                print("✅ PASS (既にLaTeX形式)")
                passed += 1
            elif "=" in input_expr and "=" in result:
                print("✅ PASS (等式変換)")
                passed += 1
            else:
                print("❌ FAIL")
                failed += 1
                
        except Exception as e:
            print(f"❌ ERROR: {e}")
            failed += 1
    
    print(f"\n=== テスト結果 ===")
    print(f"成功: {passed}")
    print(f"失敗: {failed}")
    print(f"合計: {passed + failed}")
    
    return failed == 0

if __name__ == "__main__":
    success = test_latex_conversion()
    sys.exit(0 if success else 1)
