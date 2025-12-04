def print_translation_summary():
    """"By accessing all .json files in the path of this file, prints a summary stating all keys that are missing in any locale"""
    import os
    from glob import glob
    import json
    from collections import defaultdict

    base_path = os.path.dirname(os.path.abspath(__file__))
    locale_files = glob(os.path.join(base_path, '*.json'))

    all_keys = set()
    locale_key_map = defaultdict(set)

    for file_path in locale_files:
        locale_code = os.path.splitext(os.path.basename(file_path))[0]
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            keys = set(data.keys())
            locale_key_map[locale_code] = keys
            all_keys.update(keys)

    for locale, keys in locale_key_map.items():
        missing_keys = all_keys - keys
        if missing_keys:
            print(f"Locale '{locale}' is missing {len(missing_keys)} keys:")
            for key in missing_keys:
                print(f"  - {key}")
        else:
            print(f"Locale '{locale}' has all keys.")

if __name__ == "__main__":
    print_translation_summary()
