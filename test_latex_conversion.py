#!/usr/bin/env python3
"""
LaTeX変換機能のテストスクリプト
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from latex_converter import convert_expression, convert_for_javascript
import logging

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_conversions():
    """変換テスト"""
    test_cases = [
        # 基本的な関数
        "y = sin(x)",
        "y = cos(x) + sin(x)",
        "y = tan(x)",
        "y = ln(x)",
        "y = log(x)",
        "y = sqrt(x)",
        "y = exp(x)",
        
        # 累乗と複雑な式
        "y = x^2",
        "y = x^2 + y^2",
        "y = sin(x)^2 + cos(x)^2",
        "y = e^x",
        "y = 2^x",
        
        # 分数
        "y = 1/x",
        "y = sin(x)/cos(x)",
        "y = (x+1)/(x-1)",
        
        # 3D式
        "z = x^2 + y^2",
        "z = sin(x) * cos(y)",
        "x^2 + y^2 + z^2 = 25",
        "z = sqrt(x^2 + y^2)",
        
        # 円と楕円
        "x^2 + y^2 = 1",
        "x^2/4 + y^2/9 = 1",
        
        # 極座標
        "r = sin(3*theta)",
        "r = cos(theta)",
        
        # ギリシャ文字
        "y = sin(θ)",
        "r = cos(3θ)",
        
        # 複雑な式
        "y = sin(x)^2 + cos(x)^2",
        "z = (x^2 - y^2)/(x^2 + y^2 + 1)",
        "y = (x^2 - 1)/(x + 1)",
    ]
    
    print("=" * 80)
    print("LaTeX変換テスト")
    print("=" * 80)
    
    success_count = 0
    
    for i, expr in enumerate(test_cases, 1):
        try:
            latex_result = convert_expression(expr)
            js_result = convert_for_javascript(expr)
            
            print(f"\n{i:2d}. 入力: {expr}")
            print(f"    LaTeX: {latex_result}")
            print(f"    JS用:   {js_result}")
            
            success_count += 1
            
        except Exception as e:
            print(f"\n{i:2d}. 入力: {expr}")
            print(f"    エラー: {e}")
    
    print(f"\n" + "=" * 80)
    print(f"テスト完了: {success_count}/{len(test_cases)} 成功")
    print("=" * 80)

def test_specific_case(expression):
    """特定の式をテスト"""
    print(f"\n特定テスト: {expression}")
    try:
        latex_result = convert_expression(expression)
        js_result = convert_for_javascript(expression)
        
        print(f"LaTeX: {latex_result}")
        print(f"JS用:  {js_result}")
        
    except Exception as e:
        print(f"エラー: {e}")

if __name__ == "__main__":
    # 全体テスト
    test_conversions()
    
    # 対話的テスト
    print("\n" + "=" * 80)
    print("対話的テスト（'quit'で終了）")
    print("=" * 80)
    
    while True:
        try:
            user_input = input("\n数式を入力: ").strip()
            if user_input.lower() in ['quit', 'exit', 'q']:
                break
            if user_input:
                test_specific_case(user_input)
        except KeyboardInterrupt:
            print("\n終了します...")
            break
        except Exception as e:
            print(f"エラー: {e}")