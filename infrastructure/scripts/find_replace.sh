#!/bin/sh

# Usage:
#   ./replace.sh <file> <find_text> <replace_text>

if [ "$#" -ne 3 ]; then
    echo "Usage: $0 <file> <find_text> <replace_text>" >&2
    exit 1
fi

file=$1
find_text=$2
replace_text=$3

if [ ! -f "$file" ]; then
    echo "Error: file does not exist: $file" >&2
    exit 1
fi

if [ -z "$find_text" ]; then
    echo "Error: find text cannot be empty" >&2
    exit 1
fi

tmp="$file.tmp.$$"

awk -v find="$find_text" -v replace="$replace_text" '
{
    result = ""
    text = $0

    while ((pos = index(text, find)) > 0) {
        result = result substr(text, 1, pos - 1) replace
        text = substr(text, pos + length(find))
    }

    print result text
}
' "$file" > "$tmp" || {
    rm -f "$tmp"
    exit 1
}

if ! mv "$tmp" "$file"; then
    rm -f "$tmp"
    echo "Error: could not replace original file" >&2
    exit 1
fi

echo "Updated: $file"