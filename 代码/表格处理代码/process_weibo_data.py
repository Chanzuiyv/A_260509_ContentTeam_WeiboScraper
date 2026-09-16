import os
import pandas as pd

data_dir = r'C:\Users\ThinkPad\Desktop\weibopachong\data'
output_dir = r'C:\Users\ThinkPad\Desktop\weibopachong\成员微博整理'

csv_files = [f for f in os.listdir(data_dir) if f.endswith('.csv') and f != 'member_comments.csv']
print(f'找到CSV文件: {csv_files}')

for csv_file in csv_files:
    file_path = os.path.join(data_dir, csv_file)
    member_name = csv_file.replace('.csv', '').split('-')[1]
    print(f'处理文件: {csv_file}, 成员: {member_name}')
    
    try:
        df = pd.read_csv(file_path, encoding='utf-8')
    except:
        df = pd.read_csv(file_path, encoding='gbk')
    
    print(f'数据行数: {len(df)}')
    print(f'列名: {df.columns.tolist()}')
    
    new_df = pd.DataFrame()
    new_df['成员名字'] = df['screen_name']
    new_df['发帖日期'] = df['created_at']
    new_df['微博原文'] = df['text']
    new_df['是否有图片'] = df.apply(lambda row: '√' if (pd.notna(row['pics']) and str(row['pics']) != '') or (pd.notna(row['videos']) and str(row['videos']) != '') else '❌️', axis=1)
    new_df['图片'] = df.apply(lambda row: str(row['pics']) if pd.notna(row['pics']) and str(row['pics']) != '' else str(row['videos']) if pd.notna(row['videos']) and str(row['videos']) != '' else '', axis=1)
    new_df['微博链接'] = df['url']
    new_df['是否有评论'] = ''
    new_df['评论表格链接'] = ''
    
    df['year'] = df['created_at'].apply(lambda x: str(x)[:4])
    years = df['year'].unique()
    print(f'年份: {years}')
    
    member_dir = os.path.join(output_dir, member_name)
    os.makedirs(member_dir, exist_ok=True)
    print(f'创建目录: {member_dir}')
    
    for year in sorted(years):
        year_dir = os.path.join(member_dir, str(year))
        os.makedirs(year_dir, exist_ok=True)
        
        year_df = new_df[df['year'] == year]
        year_df = year_df.drop_duplicates(subset=['微博链接'])
        
        output_file = os.path.join(year_dir, f'{year}年微博.xlsx')
        year_df.to_excel(output_file, index=False)
        print(f'已保存: {output_file}, 行数: {len(year_df)}')

print('批量处理完成！')