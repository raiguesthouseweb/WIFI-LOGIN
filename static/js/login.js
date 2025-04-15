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
    
    // Validation for room number input
    const roomInput = document.getElementById('room_number');
    if (roomInput) {
        roomInput.addEventListener('input', function(e) {
            // Limit length
            if (this.value.length > 10) {
                this.value = this.value.slice(0, 10);
            }
        });
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
            
            // If validation passes, the form will submit normally
        });
    }
});
