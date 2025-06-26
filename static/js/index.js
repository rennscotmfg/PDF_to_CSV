let uploadedData = [];

// Get DOM elements
const uploadZone = document.querySelector('.upload-zone');
const fileInput = document.getElementById('fileInput');
const fileList = document.getElementById('fileList');
const fileItems = document.getElementById('fileItems');
const uploadBtn = document.getElementById('uploadBtn');
const loading = document.getElementById('loading');
const messages = document.getElementById('messages');
const previewSection = document.getElementById('previewSection');
const downloadBtn = document.getElementById('downloadBtn');
const copyBtn = document.getElementById('copyBtn');

// Enhanced drag and drop with better visual feedback
uploadZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadZone.classList.add('dragover');
});

uploadZone.addEventListener('dragleave', (e) => {
    e.preventDefault();
    if (!uploadZone.contains(e.relatedTarget)) {
        uploadZone.classList.remove('dragover');
    }
});

uploadZone.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadZone.classList.remove('dragover');
    const files = Array.from(e.dataTransfer.files).filter(file => 
        file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf')
    );
    
    if (files.length === 0) {
        showError('Please select PDF files only.');
        return;
    }
    
    handleFiles(files);
});

fileInput.addEventListener('change', (e) => {
    const files = Array.from(e.target.files);
    handleFiles(files);
});

function handleFiles(files) {
    if (files.length === 0) return;

    // Clear previous selections
    fileItems.innerHTML = '';
    
    files.forEach((file, index) => {
        const fileItem = document.createElement('div');
        fileItem.className = 'file-item';
        fileItem.innerHTML = `
            <div class="file-info">
                <div class="file-name">[PDF] ${file.name}</div>
                <div class="file-size">${formatFileSize(file.size)} • ${new Date(file.lastModified).toLocaleDateString()}</div>
            </div>
            <div class="file-status">Ready</div>
        `;
        fileItems.appendChild(fileItem);
    });

    fileList.style.display = 'block';
    fileList.classList.add('fade-in');
    uploadBtn.onclick = () => uploadFiles(files);
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function uploadFiles(files) {
    const formData = new FormData();
    files.forEach(file => {
        formData.append('files', file);
    });

    // Show loading state
    loading.style.display = 'block';
    loading.classList.add('fade-in');
    messages.innerHTML = '';
    previewSection.style.display = 'none';
    uploadBtn.disabled = true;
    uploadBtn.textContent = 'Processing...';

    fetch('/upload', {
        method: 'POST',
        body: formData
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        loading.style.display = 'none';
        uploadBtn.disabled = false;
        uploadBtn.textContent = 'Process Files';
        
        if (data.success) {
            let successMessage = `
                [SUCCESS] Successfully processed ${data.processed_files.length} file(s)<br>
                [DATA] Extracted ${data.total_measurements} measurements<br>
                [FILES] ${data.processed_files.join(', ')}
            `;
            
            // Add OOT values information to success message
            if (data.OOT_files_count > 0) {
                successMessage += `<br>[WARNING] ${data.OOT_files_count} file(s) contain OOT values (out of tolerance): ${data.OOT_files_list.join(', ')}`;
            } else {
                successMessage += `<br>[INFO] No OOT values detected in any files`;
            }
            
            showSuccess(successMessage);
            showPreview(data);
            uploadedData = data.preview;
            
            if (data.errors && data.errors.length > 0) {
                showError('[WARNING] Some files had issues:<br>' + data.errors.join('<br>'));
            }
        } else {
            showError('[ERROR] ' + data.error + (data.details ? '<br>Details: ' + data.details.join('<br>') : ''));
        }
    })
    .catch(error => {
        loading.style.display = 'none';
        uploadBtn.disabled = false;
        uploadBtn.textContent = 'Process Files';
        showError('[ERROR] Error uploading files: ' + error.message);
        console.error('Upload error:', error);
    });
}

function showPreview(data) {
    const previewInfo = document.getElementById('previewInfo');
    let infoText = `
        Showing <strong>${data.total_parts}</strong> parts 
        with <strong>${data.total_measurements}</strong> total measurements from <strong>${data.processed_files.length}</strong> file(s)
    `;
    
    // Add OOT values summary to preview info
    if (data.OOT_files_count > 0) {
        infoText += `<br><span style="color: #dc3545; font-weight: bold;">⚠️ ${data.OOT_files_count} file(s) have OOT values (highlighted in red)</span>`;
    }
    
    previewInfo.innerHTML = infoText;
    
    // Create table headers
    const tableHead = document.getElementById('tableHead');
    const headerRow = document.createElement('tr');
    data.columns.forEach(column => {
        const th = document.createElement('th');
        th.textContent = formatColumnName(column);
        headerRow.appendChild(th);
    });
    tableHead.innerHTML = '';
    tableHead.appendChild(headerRow);

    // Create table body
    const tableBody = document.getElementById('tableBody');
    tableBody.innerHTML = '';
    data.preview.forEach((row, index) => {
        const tr = document.createElement('tr');
        
        // Check if this row has OOT values and apply styling
        const hasOOTValues = row.Has_OOT_Values === true;
        if (hasOOTValues) {
            tr.classList.add('OOT-row');
            tr.style.backgroundColor = '#ffebee';
            tr.style.borderLeft = '4px solid #f44336';
        }
        
        data.columns.forEach(column => {
            const td = document.createElement('td');
            const value = row[column];
            
            // Special handling for Has_OOT_Values column
            if (column === 'Has_OOT_Values') {
                if (value === true) {
                    td.innerHTML = '<span style="color: #f44336; font-weight: bold;">⚠️ YES</span>';
                } else {
                    td.innerHTML = '<span style="color: #4caf50;">✓ NO</span>';
                }
            } else {
                // Format values based on column type
                if (typeof value === 'number') {
                    td.textContent = parseFloat(value.toFixed(6));
                } else {
                    td.textContent = value || '';
                }
            }
            
            tr.appendChild(td);
        });
        tableBody.appendChild(tr);
    });

    previewSection.style.display = 'block';
    previewSection.classList.add('fade-in');
}

function formatColumnName(column) {
    return column
        .replace(/_/g, ' ')
        .replace(/\b\w/g, l => l.toUpperCase());
}

downloadBtn.addEventListener('click', () => {
    const includeStats = document.getElementById('includeStats').checked;
    
    downloadBtn.disabled = true;
    downloadBtn.textContent = 'Generating...';
    
    fetch('/download_csv', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            data: uploadedData,
            include_stats: includeStats
        })
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Download failed');
        }
        return response.blob();
    })
    .then(blob => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `calypso_measurements_${new Date().toISOString().slice(0,19).replace(/:/g, '-')}.csv`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        
        downloadBtn.disabled = false;
        downloadBtn.textContent = 'Download CSV';
        showSuccess('[SUCCESS] CSV file downloaded successfully!');
    })
    .catch(error => {
        downloadBtn.disabled = false;
        downloadBtn.textContent = 'Download CSV';
        showError('[ERROR] Error downloading file: ' + error.message);
        console.error('Download error:', error);
    });
});

copyBtn.addEventListener('click', () => {
    copyBtn.disabled = true;
    copyBtn.textContent = 'Copying...';

    fetch('/json_data')
        .then(response => {
            if (!response.ok) {
                throw new Error('No JSON data available to copy');
            }
            return response.json();
        })
        .then(data => {
            const jsonString = JSON.stringify(data, null, 2);
            // Use the Clipboard API
            navigator.clipboard.writeText(jsonString)
                .then(() => {
                    showSuccess('[SUCCESS] JSON copied to clipboard!');
                    copyBtn.disabled = false;
                    copyBtn.textContent = 'Copy JSON to Clipboard';
                })
                .catch(err => {
                    showError('[ERROR] Failed to copy JSON: ' + err);
                    copyBtn.disabled = false;
                    copyBtn.textContent = 'Copy JSON to Clipboard';
                });
        })
        .catch(error => {
            showError('[ERROR] ' + error.message);
            copyBtn.disabled = false;
            copyBtn.textContent = 'Copy JSON to Clipboard';
        });
});

function showError(message) {
    messages.innerHTML = `<div class="message error fade-in">${message}</div>`;
    setTimeout(() => {
        const errorMsg = messages.querySelector('.error');
        if (errorMsg) errorMsg.style.opacity = '0.7';
    }, 5000);
}

function showSuccess(message) {
    messages.innerHTML = `<div class="message success fade-in">${message}</div>`;
    setTimeout(() => {
        const successMsg = messages.querySelector('.success');
        if (successMsg) successMsg.style.opacity = '0.7';
    }, 10000);
}

// Add some interactive feedback
document.addEventListener('DOMContentLoaded', () => {
    // Add smooth scroll behavior
    document.documentElement.style.scrollBehavior = 'smooth';
    
    // Add loading states to buttons
    const buttons = document.querySelectorAll('.btn');
    buttons.forEach(btn => {
        btn.addEventListener('click', function() {
            if (!this.disabled) {
                this.style.transform = 'scale(0.98)';
                setTimeout(() => {
                    this.style.transform = '';
                }, 150);
            }
        });
    });
    
    // Add CSS for OOT rows if not already present
    if (!document.getElementById('OOT-row-styles')) {
        const style = document.createElement('style');
        style.id = 'OOT-row-styles';
        style.textContent = `
            .OOT-row {
                background-color: #ffebee !important;
                border-left: 4px solid #f44336 !important;
            }
            .OOT-row:hover {
                background-color: #ffcdd2 !important;
            }
        `;
        document.head.appendChild(style);
    }
});