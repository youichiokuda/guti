def answer_from_records(records, target_fields):
    sample = []
    for r in records[:5]:
        row = {}
        for f in target_fields:
            v = r.get(f, {})
            if isinstance(v, dict) and "value" in v:
                row[f] = v["value"]
            else:
                row[f] = v
        sample.append(row)
    return sample