"""
LaTeX変換ユーティリティ
プレーンな数学記法をLaTeX形式に変換する
"""

import re
import sympy as sp
from sympy import sympify, latex, symbols
from sympy.parsing.sympy_parser import parse_expr, standard_transformations, implicit_multiplication_application
import logging

logger = logging.getLogger(__name__)

class LaTeXConverter:
    def __init__(self):
        # 基本的な変数を定義
        self.variables = symbols('x y z t r theta phi a b c d e f g h i j k l m n o p q s u v w')
        
        # よく使われる関数の変換マップ
        self.function_map = {
            'sin': 'sin',
            'cos': 'cos', 
            'tan': 'tan',
            'sec': 'sec',
            'csc': 'csc',
            'cot': 'cot',
            'asin': 'asin',
            'acos': 'acos',
            'atan': 'atan',
            'sinh': 'sinh',
            'cosh': 'cosh',
            'tanh': 'tanh',
            'ln': 'log',
            'log': 'log',
            'exp': 'exp',
            'sqrt': 'sqrt',
            'abs': 'Abs',
            'floor': 'floor',
            'ceil': 'ceiling',
        }
        
        # ギリシャ文字の変換
        self.greek_map = {
            'alpha': r'\alpha',
            'beta': r'\beta',
            'gamma': r'\gamma',
            'delta': r'\delta',
            'epsilon': r'\epsilon',
            'theta': r'\theta',
            'lambda': r'\lambda',
            'mu': r'\mu',
            'pi': r'\pi',
            'sigma': r'\sigma',
            'phi': r'\phi',
            'omega': r'\omega'
        }
    
    def preprocess_expression(self, expr):
        """式の前処理"""
        # スペースを削除
        expr = expr.strip()
        
        # よくある記法の変換
        replacements = [
            # 累乗記法の変換
            (r'\^', '**'),
            # 絶対値記法の変換
            (r'\|([^|]+)\|', r'abs(\1)'),
            # 暗黙の乗算を明示的にする（例: 2x -> 2*x）
            (r'(\d)([a-zA-Z])', r'\1*\2'),
            (r'([a-zA-Z])(\d)', r'\1*\2'),
            (r'\)(\d)', r')*\1'),
            (r'(\d)\(', r'\1*('),
            (r'\)([a-zA-Z])', r')*\1'),
            # 関数名の後の変数を括弧で囲む準備
            (r'([a-zA-Z])\(', r'\1*('),  # これは関数以外にも適用される
        ]
        
        # 最初に関数だけを処理
        functions = ['sin', 'cos', 'tan', 'sec', 'csc', 'cot', 'asin', 'acos', 'atan', 
                    'sinh', 'cosh', 'tanh', 'ln', 'log', 'exp', 'sqrt', 'abs', 'floor', 'ceil']
        
        # 関数の後に続く変数を括弧で囲む（例: sinx -> sin(x)）
        for func in functions:
            pattern = rf'\b{func}([a-zA-Z][a-zA-Z0-9]*(?:\*[a-zA-Z0-9]+)*(?:\+[a-zA-Z0-9]+)*(?:\-[a-zA-Z0-9]+)*)'
            replacement = rf'{func}(\1)'
            expr = re.sub(pattern, replacement, expr)
        
        # 通常の置換を実行（ただし関数の括弧を避ける）
        for pattern, replacement in replacements[:-1]:  # 最後の置換は除外
            expr = re.sub(pattern, replacement, expr)
        
        # θ（シータ）をthetaに変換
        expr = expr.replace('θ', 'theta')
        expr = expr.replace('π', 'pi')
        
        return expr
    
    def convert_to_latex(self, expression):
        """プレーンな数学記法をLaTeX形式に変換（シンプルアプローチ）"""
        try:
            # 入力がすでにLaTeX形式の場合はそのまま返す
            if '\\' in expression:
                logger.info(f"入力は既にLaTeX形式のようです: {expression}")
                return expression
            
            result = expression
            
            # 累乗記法の変換（^ は既にGraTeXで使えるのでそのまま）
            # ただし ** があれば ^ に変換
            result = result.replace('**', '^')
            
            # 三角関数の変換
            trig_functions = {
                r'\bsin\(([^)]+)\)': r'\\sin\\left(\1\\right)',
                r'\bcos\(([^)]+)\)': r'\\cos\\left(\1\\right)',
                r'\btan\(([^)]+)\)': r'\\tan\\left(\1\\right)',
                r'\bsec\(([^)]+)\)': r'\\sec\\left(\1\\right)',
                r'\bcsc\(([^)]+)\)': r'\\csc\\left(\1\\right)',
                r'\bcot\(([^)]+)\)': r'\\cot\\left(\1\\right)',
                r'\basin\(([^)]+)\)': r'\\arcsin\\left(\1\\right)',
                r'\bacos\(([^)]+)\)': r'\\arccos\\left(\1\\right)',
                r'\batan\(([^)]+)\)': r'\\arctan\\left(\1\\right)',
                r'\bsinh\(([^)]+)\)': r'\\sinh\\left(\1\\right)',
                r'\bcosh\(([^)]+)\)': r'\\cosh\\left(\1\\right)',
                r'\btanh\(([^)]+)\)': r'\\tanh\\left(\1\\right)',
            }
            
            for pattern, replacement in trig_functions.items():
                result = re.sub(pattern, replacement, result)
            
            # ログ関数の変換
            result = re.sub(r'\bln\(([^)]+)\)', r'\\ln\\left(\1\\right)', result)
            result = re.sub(r'\blog\(([^)]+)\)', r'\\log\\left(\1\\right)', result)
            
            # 平方根の変換
            result = re.sub(r'\bsqrt\(([^)]+)\)', r'\\sqrt{\1}', result)
            
            # 指数関数の変換
            result = re.sub(r'\bexp\(([^)]+)\)', r'e^{\1}', result)
            
            # 絶対値の変換
            result = re.sub(r'\babs\(([^)]+)\)', r'\\left|\1\\right|', result)
            
            # 分数の変換（慎重に）
            result = self.simple_fraction_conversion(result)
            
            # ギリシャ文字の変換
            result = result.replace('θ', '\\theta')
            result = result.replace('π', '\\pi')
            
            if result != expression:
                logger.info(f"LaTeX変換: {expression} -> {result}")
            
            return result
                
        except Exception as e:
            logger.error(f"LaTeX変換エラー: {e}")
            return expression
    
    def simple_fraction_conversion(self, expr):
        """シンプルな分数変換"""
        try:
            # パターン1: 括弧で囲まれた分数 (a)/(b)
            expr = re.sub(r'\(([^)]+)\)/\(([^)]+)\)', r'\\frac{\1}{\2}', expr)
            
            # パターン2: 等式の右辺の単純分数 y = a/b
            def replace_simple_fraction(match):
                left_part = match.group(1)  # "y = " の部分
                numerator = match.group(2)   # 分子
                denominator = match.group(3) # 分母
                return f'{left_part}\\frac{{{numerator}}}{{{denominator}}}'
            
            # "=" の後の単純な分数を探す
            expr = re.sub(r'([^=]+=\s*)([^/\s]+)/([^/\s]+)(?=\s|$)', replace_simple_fraction, expr)
            
            return expr
            
        except Exception as e:
            logger.error(f"分数変換エラー: {e}")
            return expr
    
    def direct_conversion(self, expr):
        """直接的な変換（確実性重視）"""
        try:
            # 基本的な変換ルール
            conversions = [
                # 三角関数
                (r'\bsin\(([^)]+)\)', r'\\sin\\left(\1\\right)'),
                (r'\bcos\(([^)]+)\)', r'\\cos\\left(\1\\right)'),
                (r'\btan\(([^)]+)\)', r'\\tan\\left(\1\\right)'),
                (r'\bsec\(([^)]+)\)', r'\\sec\\left(\1\\right)'),
                (r'\bcsc\(([^)]+)\)', r'\\csc\\left(\1\\right)'),
                (r'\bcot\(([^)]+)\)', r'\\cot\\left(\1\\right)'),
                # 逆三角関数
                (r'\basin\(([^)]+)\)', r'\\arcsin\\left(\1\\right)'),
                (r'\bacos\(([^)]+)\)', r'\\arccos\\left(\1\\right)'),
                (r'\batan\(([^)]+)\)', r'\\arctan\\left(\1\\right)'),
                # 双曲線関数
                (r'\bsinh\(([^)]+)\)', r'\\sinh\\left(\1\\right)'),
                (r'\bcosh\(([^)]+)\)', r'\\cosh\\left(\1\\right)'),
                (r'\btanh\(([^)]+)\)', r'\\tanh\\left(\1\\right)'),
                # ログ関数
                (r'\bln\(([^)]+)\)', r'\\ln\\left(\1\\right)'),
                (r'\blog\(([^)]+)\)', r'\\log\\left(\1\\right)'),
                # 指数・平方根
                (r'\bexp\(([^)]+)\)', r'e^{\1}'),
                (r'\bsqrt\(([^)]+)\)', r'\\sqrt{\1}'),
                # 絶対値
                (r'\babs\(([^)]+)\)', r'\\left|\1\\right|'),
                # 累乗（** -> ^）
                (r'\*\*', '^'),
            ]
            
            result = expr
            for pattern, replacement in conversions:
                old_result = result
                result = re.sub(pattern, replacement, result)
                if result != old_result:
                    logger.debug(f"変換適用: {pattern} -> {old_result} => {result}")
            
            # 分数変換（より慎重に）
            result = self.convert_fractions(result)
            
            logger.info(f"直接変換完了: {expr} -> {result}")
            return result
            
        except Exception as e:
            logger.error(f"直接変換エラー: {e}")
            return expr
    
    def convert_fractions(self, expr):
        """分数変換の専用関数"""
        try:
            # パターン1: 括弧で囲まれた分数 (a)/(b)
            expr = re.sub(r'\(([^)]+)\)/\(([^)]+)\)', r'\\frac{\1}{\2}', expr)
            
            # パターン2: 単純な分数 a/b (=を含まない場合)
            if '=' not in expr:
                # 全体が分数の場合
                fraction_match = re.match(r'^([^/]+)/([^/]+)$', expr.strip())
                if fraction_match:
                    return f'\\frac{{{fraction_match.group(1)}}}{{{fraction_match.group(2)}}}'
            
            # パターン3: 等式の右辺の分数
            def replace_right_side_fraction(match):
                left = match.group(1)
                right = match.group(2)
                # 右辺に分数がある場合
                fraction_match = re.search(r'([^/\s=]+)/([^/\s]+)', right)
                if fraction_match:
                    numerator = fraction_match.group(1)
                    denominator = fraction_match.group(2)
                    new_right = right.replace(f'{numerator}/{denominator}', f'\\frac{{{numerator}}}{{{denominator}}}')
                    return f'{left}= {new_right}'
                return match.group(0)
            
            expr = re.sub(r'([^=]+)=\s*(.+)', replace_right_side_fraction, expr)
            
            return expr
            
        except Exception as e:
            logger.error(f"分数変換エラー: {e}")
            return expr
    
    def postprocess_latex(self, latex_expr):
        """LaTeX式の後処理"""
        # 三角関数の引数を \left( \right) で囲む
        trig_functions = ['sin', 'cos', 'tan', 'sec', 'csc', 'cot', 'asin', 'acos', 'atan', 'sinh', 'cosh', 'tanh']
        
        for func in trig_functions:
            # \sin{x} -> \sin\left(x\right) の形式に変換
            pattern = rf'\\{func}\{{([^}}]+)\}}'
            replacement = rf'\\{func}\\left(\1\\right)'
            latex_expr = re.sub(pattern, replacement, latex_expr)
        
        # ログ関数の処理
        latex_expr = re.sub(r'\\log\{([^}]+)\}', r'\\log\\left(\1\\right)', latex_expr)
        
        # 平方根の処理
        latex_expr = re.sub(r'\\sqrt\{([^}]+)\}', r'\\sqrt{\1}', latex_expr)
        
        return latex_expr
    
    def manual_conversion(self, expr):
        """手動変換（フォールバック）"""
        try:
            # 基本的な変換ルール
            conversions = [
                # 三角関数
                (r'\bsin\(([^)]+)\)', r'\\sin\\left(\1\\right)'),
                (r'\bcos\(([^)]+)\)', r'\\cos\\left(\1\\right)'),
                (r'\btan\(([^)]+)\)', r'\\tan\\left(\1\\right)'),
                # ログ関数
                (r'\bln\(([^)]+)\)', r'\\ln\\left(\1\\right)'),
                (r'\blog\(([^)]+)\)', r'\\log\\left(\1\\right)'),
                # 平方根
                (r'\bsqrt\(([^)]+)\)', r'\\sqrt{\1}'),
                # 累乗（** -> ^）
                (r'\*\*', '^'),
                # 分数記法の検出と変換
                (r'([^/]+)/([^/]+)', r'\\frac{\1}{\2}'),
            ]
            
            result = expr
            for pattern, replacement in conversions:
                result = re.sub(pattern, replacement, result)
            
            logger.info(f"手動変換完了: {expr} -> {result}")
            return result
            
        except Exception as e:
            logger.error(f"手動変換エラー: {e}")
            return expr
    
    def convert_for_desmos(self, latex_expr):
        """LaTeX式をDesmos/GraTeX用にエスケープ"""
        # JavaScriptで使用するために \\ でエスケープ
        escaped = latex_expr.replace('\\', '\\\\')
        return escaped

# グローバルコンバーター
latex_converter = LaTeXConverter()

def convert_expression(expression):
    """式を変換する便利関数"""
    return latex_converter.convert_to_latex(expression)

def convert_for_javascript(expression):
    """JavaScript用にエスケープした式を取得"""
    latex_expr = latex_converter.convert_to_latex(expression)
    return latex_converter.convert_for_desmos(latex_expr)
