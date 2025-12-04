function initGoogleLogin(clientId, domId) {
    console.log("Init Google Login (Redirect Mode)");

    if (typeof google === 'undefined') {
        console.error("CRITICAL: Google Client Library not loaded.");
        return;
    }

    google.accounts.id.initialize({
        client_id: clientId,
        use_fedcm_for_prompt: false,
        ux_mode: 'popup', 
        context: 'signin',
        callback: function(response) {
            console.log("GOOGLE CALLBACK RECEIVED");
            
            if (response.credential) {
                console.log("✅ Token received. Redirecting to backend verification...");
                
                // Navigate to the callback page with token as query param.
                var token = response.credential;
                window.location.href = '/auth/google/callback?token=' + encodeURIComponent(token);
                
            } else {
                console.error("No credential in response.");
            }
        }
    });

    // Render Button
    var targetDiv = document.getElementById(domId);
    if (targetDiv) {
        google.accounts.id.renderButton(
            targetDiv,
            { theme: "filled_black", size: "large", shape: "pill", width: "250" }
        );
    }
}
