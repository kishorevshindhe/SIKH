with open('frontend/search.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Remove the wrongly placed loadFilesIntoCorpus call at bottom
content = content.replace(
    "    // Load user files into search on page load\n    loadFilesIntoCorpus();\n  </script>",
    "  </script>"
)

# Find the IDF line and add the call right after it
old = "    const IDF = computeIDF(CORPUS);"

new = """    const IDF = computeIDF(CORPUS);

    // Load real user files into corpus from backend
    (async () => {
      const token = localStorage.getItem('token');
      if (!token) return;
      try {
        const response = await fetch('http://127.0.0.1:9000/library/files', {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        if (!response.ok) return;
        const files = await response.json();
        files.forEach((file, index) => {
          const type = file.filename.toLowerCase().endsWith('.pdf') ? 'pdf' :
                       file.filename.toLowerCase().endsWith('.docx') ? 'notes' :
                       file.filename.toLowerCase().endsWith('.txt') ? 'notes' : 'pdf';
          CORPUS.push({
            id: 100 + index,
            type: type,
            title: file.filename.replace(/\\.[^/.]+$/, ''),
            path: `/library/download/${file.file_id}`,
            date: file.uploaded_at ? file.uploaded_at.split(' ')[0] : '2026-01-01',
            size: file.filesize ? (file.filesize / (1024*1024)).toFixed(1) + ' MB' : '0.0 MB',
            content: file.content_text || file.filename.replace(/\\.[^/.]+$/, '')
          });
        });
        console.log('Loaded', files.length, 'user files into search corpus');
      } catch(e) {
        console.error('Failed to load files into search corpus:', e);
      }
    })();"""

content = content.replace(old, new)

with open('frontend/search.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("Done!")