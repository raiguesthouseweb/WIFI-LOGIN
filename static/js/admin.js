document.addEventListener('DOMContentLoaded', function() {
    // Initialize variables
    const refreshBtn = document.getElementById('refreshBtn');
    const refreshSheetBtn = document.getElementById('refreshSheetBtn');
    const refreshSpinner = document.getElementById('refreshSpinner');
    const userTableBody = document.getElementById('userTableBody');
    const disconnectModal = new bootstrap.Modal(document.getElementById('disconnectModal'));
    const disconnectUserName = document.getElementById('disconnectUserName');
    const confirmDisconnectBtn = document.getElementById('confirmDisconnectBtn');
    let currentUserId = null;
    let chartInstance = null;
    
    // Format bytes to human-readable format
    function formatBytes(bytes, decimals = 2) {
        if (bytes === 0) return '0 Bytes';
        
        const k = 1024;
        const dm = decimals < 0 ? 0 : decimals;
        const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
        
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        
        return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
    }
    
    // Update statistics
    function updateStats(users) {
        // Update connected users count
        document.getElementById('connectedUsersCount').textContent = users.length;
        
        // Calculate total download and upload
        let totalDownload = 0;
        let totalUpload = 0;
        
        users.forEach(user => {
            totalDownload += parseInt(user.bytes_in || 0);
            totalUpload += parseInt(user.bytes_out || 0);
        });
        
        // Update statistics displays
        document.getElementById('totalDownload').textContent = formatBytes(totalDownload);
        document.getElementById('totalUpload').textContent = formatBytes(totalUpload);
        
        // Update chart data
        updateChart(totalDownload, totalUpload);
    }
    
    // Initialize chart
    function initChart() {
        const ctx = document.getElementById('usageChart').getContext('2d');
        
        chartInstance = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: ['Download', 'Upload'],
                datasets: [{
                    label: 'Network Usage (MB)',
                    data: [0, 0],
                    backgroundColor: [
                        'rgba(40, 167, 69, 0.6)',  // Green for download
                        'rgba(220, 53, 69, 0.6)'   // Red for upload
                    ],
                    borderColor: [
                        'rgba(40, 167, 69, 1)',
                        'rgba(220, 53, 69, 1)'
                    ],
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: function(value) {
                                return formatBytes(value);
                            }
                        }
                    }
                }
            }
        });
    }
    
    // Update chart data
    function updateChart(download, upload) {
        if (chartInstance) {
            chartInstance.data.datasets[0].data = [download, upload];
            chartInstance.update();
        }
    }
    
    // Initialize chart on load
    initChart();
    
    // Refresh user data
    function refreshUserData() {
        refreshSpinner.classList.remove('d-none');
        
        fetch('/api/users')
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Update users table
                    updateUsersTable(data.users);
                    
                    // Update statistics
                    updateStats(data.users);
                } else {
                    console.error('Failed to fetch users:', data.error);
                    alert('Failed to refresh user data: ' + data.error);
                }
            })
            .catch(error => {
                console.error('Error fetching users:', error);
                alert('Error fetching user data. Please try again.');
            })
            .finally(() => {
                refreshSpinner.classList.add('d-none');
            });
    }
    
    // Update users table
    function updateUsersTable(users) {
        // Clear table
        userTableBody.innerHTML = '';
        
        if (users.length === 0) {
            // Show no users message
            const row = document.createElement('tr');
            row.id = 'noUsersRow';
            row.innerHTML = `
                <td colspan="6" class="text-center py-4">
                    <i class="fas fa-users-slash fa-2x mb-2 text-muted"></i>
                    <p class="mb-0">No users currently connected</p>
                </td>
            `;
            userTableBody.appendChild(row);
        } else {
            // Add users to table
            users.forEach(user => {
                const row = document.createElement('tr');
                row.dataset.userId = user.id;
                
                // Format data usage
                const bytesIn = parseInt(user.bytes_in || 0);
                const bytesOut = parseInt(user.bytes_out || 0);
                const bytesInMB = (bytesIn / 1024 / 1024).toFixed(2);
                const bytesOutMB = (bytesOut / 1024 / 1024).toFixed(2);
                
                row.innerHTML = `
                    <td>${user.user}</td>
                    <td>${user.address}</td>
                    <td>${user.mac_address}</td>
                    <td>${user.uptime}</td>
                    <td>
                        <i class="fas fa-arrow-down text-success me-1"></i>${bytesInMB} MB
                        <br>
                        <i class="fas fa-arrow-up text-danger me-1"></i>${bytesOutMB} MB
                    </td>
                    <td>
                        <button class="btn btn-sm btn-danger disconnect-btn" data-user-id="${user.id}" data-user-name="${user.user}">
                            <i class="fas fa-ban me-1"></i>Disconnect
                        </button>
                    </td>
                `;
                
                userTableBody.appendChild(row);
            });
            
            // Add event listeners to disconnect buttons
            const disconnectButtons = document.querySelectorAll('.disconnect-btn');
            disconnectButtons.forEach(button => {
                button.addEventListener('click', function() {
                    const userId = this.dataset.userId;
                    const userName = this.dataset.userName;
                    
                    // Set values for modal
                    disconnectUserName.textContent = userName;
                    currentUserId = userId;
                    
                    // Show modal
                    disconnectModal.show();
                });
            });
        }
    }
    
    // Disconnect user
    function disconnectUser(userId) {
        const formData = new FormData();
        formData.append('user_id', userId);
        
        fetch('/api/disconnect_user', {
            method: 'POST',
            body: formData
        })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Hide modal
                    disconnectModal.hide();
                    
                    // Refresh user data
                    refreshUserData();
                    
                    // Show success message
                    alert('User disconnected successfully');
                } else {
                    console.error('Failed to disconnect user:', data.error);
                    alert('Failed to disconnect user: ' + data.error);
                }
            })
            .catch(error => {
                console.error('Error disconnecting user:', error);
                alert('Error disconnecting user. Please try again.');
            });
    }
    
    // Refresh Google Sheet data
    function refreshSheetData() {
        fetch('/api/refresh_sheet')
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    alert('Google Sheet data refreshed successfully');
                } else {
                    console.error('Failed to refresh sheet data:', data.error);
                    alert('Failed to refresh sheet data: ' + data.error);
                }
            })
            .catch(error => {
                console.error('Error refreshing sheet data:', error);
                alert('Error refreshing sheet data. Please try again.');
            });
    }
    
    // Event: Refresh button click
    if (refreshBtn) {
        refreshBtn.addEventListener('click', refreshUserData);
    }
    
    // Event: Refresh Sheet button click
    if (refreshSheetBtn) {
        refreshSheetBtn.addEventListener('click', refreshSheetData);
    }
    
    // Event: Confirm disconnect button click
    if (confirmDisconnectBtn) {
        confirmDisconnectBtn.addEventListener('click', function() {
            if (currentUserId) {
                disconnectUser(currentUserId);
            }
        });
    }
    
    // Auto-refresh every 30 seconds
    const autoRefreshInterval = setInterval(refreshUserData, 30000);
    
    // Initial data load
    refreshUserData();
});
