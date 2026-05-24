with open('frontend/files.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Move openFile function outside deleteFile
old = """      renderLibrary();
async function openFile(fileId) {
  try {
    const token = localStorage.getItem('token');
    const response = await fetch(
      `http://127.0.0.1:9000/library/download/${fileId}`,
      {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      }
    );
    if (!response.ok) {
      throw new Error('Failed to open file');
    }
    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    window.open(url, '_blank');
  }
  catch(error) {
    console.error(error);
    alert('Unable to open file');
  }
}
      updateFileCount();"""

new = """      renderLibrary();
      updateFileCount();"""

content = content.replace(old, new)

# Add openFile before confirmBulkDelete
old2 = """    function confirmBulkDelete() {"""

new2 = """    async function openFile(fileId) {
      try {
        const token = localStorage.getItem('token');
        const response = await fetch(
          `http://127.0.0.1:9000/library/download/${fileId}`,
          {
            headers: {
              'Authorization': `Bearer ${token}`
            }
          }
        );
        if (!response.ok) {
          throw new Error('Failed to open file');
        }
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        window.open(url, '_blank');
      }
      catch(error) {
        console.error(error);
        alert('Unable to open file');
      }
    }

    function confirmBulkDelete() {"""

content = content.replace(old2, new2)

with open('frontend/files.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("Done! openFile function fixed.")