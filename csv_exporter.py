import pandas as pd
from io import BytesIO

def generate_transposed_csv(df, include_stats=False):
    output = BytesIO()
    dim_cols = [col for col in df.columns if col not in ['Part_Number', 'Source_File', 'Unit']]

    transposed_data = {'Dimension': dim_cols}
    for _, row in df.iterrows():
        part = f"{row['Part_Number']} ({row['Source_File']})"
        transposed_data[part] = [round(row[col], 6) if pd.notna(row[col]) else '' for col in dim_cols]

    transposed_df = pd.DataFrame(transposed_data)

    if include_stats:
        transposed_df['Count_Parts_Measured'] = [df[col].count() for col in dim_cols]
        transposed_df['Mean_Value'] = [round(df[col].mean(), 6) if df[col].count() > 0 else '' for col in dim_cols]
        transposed_df['Min_Value'] = [round(df[col].min(), 6) if df[col].count() > 0 else '' for col in dim_cols]
        transposed_df['Max_Value'] = [round(df[col].max(), 6) if df[col].count() > 0 else '' for col in dim_cols]
        transposed_df['Std_Dev'] = [round(df[col].std(), 6) if df[col].count() > 1 else '' for col in dim_cols]

    transposed_df['Unit'] = [df['Unit'].iloc[0] for _ in dim_cols]

    output.write(b"# Calypso CMM Measurement Data - Transposed Format\n")
    output.write(b"# Rows = Dimensions, Columns = Parts\n")
    output.write(f"# Generated: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n".encode())
    transposed_df.to_csv(output, index=False, lineterminator='\n')
    output.seek(0)
    return output
