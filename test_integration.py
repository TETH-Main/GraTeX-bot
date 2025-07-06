#!/usr/bin/env python3
"""
LaTeX変換統合テストスクリプト
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from latex_converter import convert_expression, convert_for_javascript
import logging

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_integration():
    """統合テスト"""
    test_cases = [
        # ユーザーが実際に入力しそうな式
        "y = sin(x)",
        "y = x^2",
        "y = 1/x",
        "y = sqrt(x)",
        "y = exp(x)",
        "z = x^2 + y^2",
        "z = sin(x) * cos(y)",
        "x^2 + y^2 = 1",
        "r = cos(3θ)",
        "y = (x+1)/(x-1)",
    ]
    
    print("=" * 80)
    print("LaTeX変換統合テスト")
    print("=" * 80)
    
    for i, expr in enumerate(test_cases, 1):
        try:
            latex_result = convert_expression(expr)
            js_result = convert_for_javascript(expr)
            
            print(f"\n{i:2d}. 入力: {expr}")
            if latex_result != expr:
                print(f"    変換: {latex_result}")
            else:
                print(f"    変換: (変換なし)")
            print(f"    JS用: {js_result}")
            
        except Exception as e:
            print(f"\n{i:2d}. 入力: {expr}")
            print(f"    エラー: {e}")
    
    print(f"\n" + "=" * 80)
    print("統合テスト完了")
    print("=" * 80)

if __name__ == "__main__":
    test_integration()
