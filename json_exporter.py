import json

def export_json(df):

    output = []
    for col in df.columns:
        if col.startswith("DIM"):
            tag = col.replace("DIM", "")  # Extract the number after 'DIM'
            values = df[col].astype(str).tolist()
            output.append({
                "tag": tag,
                "values": values
            })

    return json.dumps(output)