import pdfplumber
import pandas as pd
import re
import os

pdf = pdfplumber.open('test.pdf')
text = ''
for page in pdf.pages:
    text += page.extract_text()

unstructured_lines = text.split('\n')

lines = []

for line in unstructured_lines:
    word_list = line.split()
    if len(word_list) > 1:
        for i, word in enumerate(word_list):
            if word.startswith('DIM#'):
                lines.append(word_list[i:])


dim_list = []

for line in lines:
    dim_name = line[0].split('#')[1]
    entry = {'tag': dim_name, 'values': []}
    dim_list.append(entry)

for line in lines:
    dim_name = line[0].split('#')[1]
    value = line[1]
    for entry in dim_list:
        if entry['tag'] == dim_name:
            entry['values'].append(value)

def normalize_tag(tag):
    match = re.match(r"(\d+)", tag)
    return match.group(1) if match else None

def get_priority(tag):
    tag_upper = tag.upper()
    if "(M)" in tag_upper:
        return 1
    elif re.fullmatch(r"\d+", tag):
        return 2
    elif "MIN" in tag_upper:
        return 3
    else:
        return 4

def prioritize_tags(data):
    prioritized = {}
    for entry in data:
        base = normalize_tag(entry["tag"])
        if not base:
            continue
        priority = get_priority(entry["tag"])
        if base not in prioritized:
            prioritized[base] = (priority, entry)
        else:
            existing_priority, _ = prioritized[base]
            # Replace only if new one has higher priority (lower number)
            if priority < existing_priority:
                prioritized[base] = (priority, entry)
            # If same priority, keep the first one encountered (do nothing)

    # Replace 'tag' with only base number in output
    result = []
    for base, (_, entry) in sorted(prioritized.items(), key=lambda x: int(x[0])):
        result.append({
            "tag": base,
            "values": entry["values"]
        })
    return result

filtered = prioritize_tags(dim_list)

df = pd.DataFrame(filtered)

print(df)
