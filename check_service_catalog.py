import sys
import io
import pandas as pd

# UTF-8出力を強制
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

df = pd.read_excel('docs/0602_service-offerings-catalog_reviewed.xlsx')

print("=== サービスカタログデータ構造 ===\n")
print(f"総行数: {len(df)}")
print(f"カラム数: {len(df.columns)}\n")

print("=== カラム一覧 ===")
for i, col in enumerate(df.columns, 1):
    print(f"{i:2d}. {col}")

print("\n=== 最初の3件のデータ ===")
for idx in range(min(3, len(df))):
    print(f"\n【サービス {idx+1}】")
    row = df.iloc[idx]
    for col in df.columns:
        val = row[col]
        if pd.notna(val):
            print(f"  {col}: {val}")

print("\n=== Direction の分布 ===")
print(df['direction'].value_counts())

print("\n=== Domain の分布 ===")
print(df['domain'].value_counts())

print("\n=== Value Shift の分布 ===")
print(df['value_shift_1'].value_counts())
