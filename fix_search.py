with open('frontend/search.html', 'r', encoding='utf-8') as f:
    content = f.read()

old = """    ];
    const STOP = new Set(["""

new = """    ];

    // Load real files from backend and add to CORPUS
    async function loadFilesIntoCorpus() {
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
      } catch(e) {
        console.error('Failed to load files into search corpus:', e);
      }
    }

    const STOP = new Set(["""

content = content.replace(old, new)

# Also add loadFilesIntoCorpus() call at the end before </script>
old2 = """  </script>
</body>
</html>"""

new2 = """    // Load user files into search on page load
    loadFilesIntoCorpus();
  </script>
</body>
</html>"""

content = content.replace(old2, new2)

with open('frontend/search.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("Done! Search corpus connected to backend.")