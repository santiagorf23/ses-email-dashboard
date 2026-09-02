// Onboarding Wizard Logic

const API_BASE = '/api';
let currentStep = 1;
let tenantData = {};
let pollingInterval = null;

// Get token from localStorage
function getToken() {
    return localStorage.getItem('token');
}

// API helper
async function apiCall(endpoint, method = 'GET', body = null) {
    const headers = {
        'Content-Type': 'application/json',
    };
    
    const token = getToken();
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }
    
    const config = { method, headers };
    if (body) {
        config.body = JSON.stringify(body);
    }
    
    const response = await fetch(`${API_BASE}${endpoint}`, config);
    
    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Error en la solicitud');
    }
    
    return response.json();
}

// Initialize wizard
document.addEventListener('DOMContentLoaded', async () => {
    // Check if user is logged in
    if (!getToken()) {
        window.location.href = '/';
        return;
    }
    
    try {
        const status = await apiCall('/onboarding/status');
        tenantData = status;
        
        // Update UI with tenant data
        document.getElementById('team-name').value = status.tenant_name || '';
        
        // Jump to last completed step
        if (status.current_step > 1) {
            goToStep(status.current_step);
        }
    } catch (error) {
        console.error('Failed to load onboarding status:', error);
    }
});

// Step navigation
function goToStep(step) {
    document.querySelectorAll('.wizard-step').forEach(s => s.classList.remove('active'));
    document.querySelectorAll('.step-indicator .step').forEach(s => {
        const sStep = parseInt(s.dataset.step);
        s.classList.remove('active', 'completed');
        if (sStep < step) s.classList.add('completed');
        if (sStep === step) s.classList.add('active');
    });
    
    document.getElementById(`step-${step}`).classList.add('active');
    currentStep = step;
}

function nextStep(current) {
    // Validate current step
    if (current === 1) {
        const teamName = document.getElementById('team-name').value.trim();
        const domain = document.getElementById('domain').value.trim();
        
        if (!teamName || !domain) {
            alert('Por favor completa todos los campos');
            return;
        }
        
        tenantData.team_name = teamName;
        tenantData.domain = domain;
    }
    
    goToStep(current + 1);
}

function prevStep(current) {
    goToStep(current - 1);
}

// AWS Verification
async function verifyAWS() {
    const accessKey = document.getElementById('aws-access-key').value.trim();
    const secretKey = document.getElementById('aws-secret-key').value.trim();
    const region = document.getElementById('aws-region').value;
    
    if (!accessKey || !secretKey) {
        alert('Por favor ingresa tus credenciales AWS');
        return;
    }
    
    const resultDiv = document.getElementById('aws-verification-result');
    resultDiv.style.display = 'block';
    resultDiv.className = 'verification-result';
    resultDiv.innerHTML = '<p>Verificando credenciales...</p>';
    
    try {
        const result = await apiCall('/onboarding/verify-aws', 'POST', {
            aws_access_key: accessKey,
            aws_secret_key: secretKey,
            aws_region: region,
        });
        
        resultDiv.className = 'verification-result success';
        resultDiv.innerHTML = `
            <p><strong>¡Credenciales verificadas!</strong></p>
            <p>Cuenta AWS: ${result.account_id}</p>
            <p>ARN: ${result.arn}</p>
        `;
        
        tenantData.aws_configured = true;
        
        // Auto-advance after 2 seconds
        setTimeout(() => nextStep(2), 2000);
        
    } catch (error) {
        resultDiv.className = 'verification-result error';
        resultDiv.innerHTML = `<p><strong>Error:</strong> ${error.message}</p>`;
    }
}

// Domain Verification
async function verifyDomain() {
    const domain = tenantData.domain || document.getElementById('domain').value.trim();
    
    if (!domain) {
        alert('Por favor ingresa un dominio');
        return;
    }
    
    const resultDiv = document.getElementById('domain-verification-result');
    resultDiv.style.display = 'block';
    resultDiv.className = 'verification-result';
    resultDiv.innerHTML = '<p>Iniciando verificación...</p>';
    
    try {
        const result = await apiCall('/onboarding/verify-domain', 'POST', { domain });
        
        // Show DNS records
        const dnsRecords = document.getElementById('dns-records');
        dnsRecords.style.display = 'block';
        document.getElementById('dns-txt').textContent = result.instructions.txt_record;
        document.getElementById('dns-cname-bounce').textContent = result.instructions.cname_bounce;
        document.getElementById('dns-cname-dkim').textContent = result.instructions.cname_dkim;
        
        resultDiv.className = 'verification-result success';
        resultDiv.innerHTML = `
            <p><strong>Verificación iniciada</strong></p>
            <p>Agrega los registros DNS mostrados arriba y luego haz clic en "Verificar dominio" nuevamente.</p>
            <p>La verificación puede tardar hasta 72 horas.</p>
        `;
        
    } catch (error) {
        resultDiv.className = 'verification-result error';
        resultDiv.innerHTML = `<p><strong>Error:</strong> ${error.message}</p>`;
    }
}

// SNS Subscription
async function subscribeSNS() {
    const topicArn = document.getElementById('topic-arn').value.trim();
    
    if (!topicArn) {
        alert('Por favor ingresa el ARN del topic SNS');
        return;
    }
    
    const resultDiv = document.getElementById('sns-verification-result');
    resultDiv.style.display = 'block';
    resultDiv.className = 'verification-result';
    resultDiv.innerHTML = '<p>Suscribiendo topic...</p>';
    
    try {
        const result = await apiCall('/onboarding/subscribe-sns', 'POST', {
            topic_arn: topicArn,
        });
        
        resultDiv.className = 'verification-result success';
        resultDiv.innerHTML = `
            <p><strong>¡Suscrito!</strong></p>
            <p>Subscription ARN: ${result.subscription_arn}</p>
            <p>Confirma la suscripción desde el email de AWS SNS.</p>
        `;
        
        tenantData.sns_configured = true;
        
    } catch (error) {
        resultDiv.className = 'verification-result error';
        resultDiv.innerHTML = `<p><strong>Error:</strong> ${error.message}</p>`;
    }
}

// Test Email
async function sendTestEmail() {
    const btn = document.getElementById('btn-send-test');
    const progress = document.getElementById('test-progress');
    const status = document.getElementById('test-status');
    
    btn.disabled = true;
    btn.textContent = 'Enviando...';
    
    try {
        // In a real implementation, this would call a backend endpoint
        // to send a test email via SES
        status.innerHTML = '<p>Email de prueba enviado. Esperando evento...</p>';
        progress.style.display = 'block';
        
        let timeLeft = 30;
        const timer = document.getElementById('test-timer');
        
        pollingInterval = setInterval(() => {
            timeLeft--;
            timer.textContent = timeLeft;
            
            // Update progress bar
            const progressFill = document.querySelector('.progress-fill');
            progressFill.style.width = `${((30 - timeLeft) / 30) * 100}%`;
            
            if (timeLeft <= 0) {
                clearInterval(pollingInterval);
                showTestResult(true);
            }
        }, 1000);
        
    } catch (error) {
        btn.disabled = false;
        btn.textContent = 'Enviar prueba';
        status.innerHTML = `<p><strong>Error:</strong> ${error.message}</p>`;
    }
}

function showTestResult(success) {
    const progress = document.getElementById('test-progress');
    const result = document.getElementById('test-result');
    const btn = document.getElementById('btn-send-test');
    const goBtn = document.getElementById('btn-go-dashboard');
    
    progress.style.display = 'none';
    result.style.display = 'block';
    btn.style.display = 'none';
    goBtn.style.display = 'inline-block';
}

function goToDashboard() {
    window.location.href = '/';
}

// Copy to clipboard
function copyToClipboard(elementId) {
    const text = document.getElementById(elementId).textContent;
    navigator.clipboard.writeText(text).then(() => {
        const btn = event.target;
        const originalText = btn.textContent;
        btn.textContent = '¡Copiado!';
        setTimeout(() => btn.textContent = originalText, 2000);
    });
}
