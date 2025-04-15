document.addEventListener('DOMContentLoaded', function() {
    // Validation for mobile number input
    const mobileInput = document.getElementById('mobile_number');
    if (mobileInput) {
        mobileInput.addEventListener('input', function(e) {
            // Allow only digits
            this.value = this.value.replace(/[^0-9]/g, '');
            
            // Limit length
            if (this.value.length > 15) {
                this.value = this.value.slice(0, 15);
            }
        });
    }
    
    // Validation for room number input - less restrictive to allow various formats
    const roomInput = document.getElementById('room_number');
    if (roomInput) {
        roomInput.addEventListener('input', function(e) {
            // Limit length
            if (this.value.length > 15) {
                this.value = this.value.slice(0, 15);
            }
            
            // Convert to uppercase for better user experience
            // Don't replace spaces to allow formats like "R 0" or "1 Dorm"
            this.value = this.value.toUpperCase();
        });
    }
    
    // Helper function to format room number
    function formatRoomNumber(roomNumber) {
        // This function could be expanded if needed to help format the room number
        // as the user types, making suggestions or auto-corrections
        // For now, we'll just return the value as is
        return roomNumber;
    }
    
    // Form submission
    const loginForm = document.getElementById('loginForm');
    if (loginForm) {
        loginForm.addEventListener('submit', function(e) {
            // Basic validation
            const mobile = mobileInput.value.trim();
            const room = roomInput.value.trim();
            
            if (!mobile) {
                e.preventDefault();
                alert('Please enter your mobile number');
                mobileInput.focus();
                return false;
            }
            
            if (!room) {
                e.preventDefault();
                alert('Please enter your room number');
                roomInput.focus();
                return false;
            }
            
            // Show a message to indicate the form is being submitted
            const submitBtn = this.querySelector('button[type="submit"]');
            if (submitBtn) {
                submitBtn.innerHTML = '<i class="fas fa-circle-notch fa-spin me-2"></i>Connecting...';
                submitBtn.disabled = true;
            }
            
            // Form will submit normally
        });
    }
    
    // Add helpful tooltip or placeholder text
    if (roomInput) {
        roomInput.setAttribute('placeholder', 'e.g., R0, F1, 1 Dorm');
        roomInput.setAttribute('title', 'Enter your room number (R0, F1, 1 Dorm, etc.)');
    }
});
