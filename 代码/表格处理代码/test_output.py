import pandas as pd

df = pd.read_excel(r'C:\Users\ThinkPad\Desktop\weibopachong\成员微博整理\顾子尧\2026\2026年微博.xlsx')
print('Columns:', df.columns.tolist())
print('\\nSample data:')
for i in range(min(3, len(df))):
    row = df.iloc[i]
    print(f'Row {i}:')
    print(f'  成员名字: {row['成员名字']}')
    print(f'  发帖日期: {row['发帖日期']}')
    print(f'  微博原文: {row['微博原文']}')
    has_image = row['是否有图片']
    print(f'  是否有图片: {has_image}')
    img_link = row['图片']
    print(f'  图片链接: {img_link}')
    print(f'  微博链接: {row['微博链接']}')
    print()