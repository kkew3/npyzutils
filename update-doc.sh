#!/bin/bash
find src/ -maxdepth 1 -mindepth 1 -type f \
| while read -r filename; do
	prog="$(basename "$filename")"
	echo "# $prog" > doc/$prog.txt
	echo '```' >> doc/$prog.txt
	python "$filename" -h >> doc/$prog.txt
	echo '```' >> doc/$prog.txt
	echo >> doc/$prog.txt
done
rm -f doc/index.html doc/index.md
paste -sd'\n' doc/*.txt > doc/index.md
pandoc -o doc/index.html doc/index.md
rm doc/index.md
rm doc/*.txt
