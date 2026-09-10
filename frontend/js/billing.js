/**
 * Billing Page - MailPulse
 * Maneja la integración con LemonSqueezy para pagos.
 */

// ═══════════════════════════════════════════════════
// CONFIG
// ═══════════════════════════════════════════════════

const API = window.location.origin + '/api';

// XSS protection
function esc(s) {
  const d = document.createElement('div');
  d.appendChild(document.createTextNode(s));
  return d.innerHTML;
}

// ═══════════════════════════════════════════════════
// STATE
// ═══════════════════════════════════════════════════

let currentPlan = 'free';
let billingInterval = 'monthly';

// ═══════════════════════════════════════════════════
// INIT
// ═══════════════════════════════════════════════════

document.addEventListener('DOMContentLoaded', async () => {
  // Check auth
  if (!localStorage.getItem(CONFIG?.TOKEN_KEY || 'ses_token')) {
    window.location.href = '/';
    return;
  }

  // Load current subscription
  await loadSubscription();
  
  // Load invoices
  await loadInvoices();
  
  // Setup billing toggle
  setupBillingToggle();
});

// ═══════════════════════════════════════════════════
// API CALLS
// ═══════════════════════════════════════════════════

async function loadSubscription() {
  try {
    const response = await fetch(`${API}/billing/subscription`, {
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('ses_token')}`
      }
    });

    if (response.ok) {
      const data = await response.json();
      currentPlan = data.plan_name;
      updatePlanUI(data);
    }
  } catch (error) {
    logger.error('Error loading subscription:', error);
  }
}

async function loadInvoices() {
  try {
    const response = await fetch(`${API}/billing/invoices`, {
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('ses_token')}`
      }
    });

    if (response.ok) {
      const data = await response.json();
      updateInvoicesTable(data.invoices);
    }
  } catch (error) {
    logger.error('Error loading invoices:', error);
  }
}

async function upgradePlan(planId) {
  try {
    // Adjust plan ID based on billing interval
    const adjustedPlan = billingInterval === 'annual' 
      ? planId.replace('_monthly', '_annual')
      : planId;

    const response = await fetch(`${API}/billing/checkout`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('ses_token')}`
      },
      body: JSON.stringify({ plan: adjustedPlan })
    });

    if (response.ok) {
      const data = await response.json();
      // Redirect to LemonSqueezy checkout
      window.location.href = data.checkout_url;
    } else {
      const error = await response.json();
      alert('Error: ' + (error.detail || 'Failed to create checkout'));
    }
  } catch (error) {
    logger.error('Error upgrading plan:', error);
    alert('Error al procesar el pago. Por favor, intenta de nuevo.');
  }
}

async function cancelSubscription() {
  if (!confirm('Are you sure you want to cancel your subscription? You will lose access to premium features at the end of your billing period.')) {
    return;
  }

  try {
    const response = await fetch(`${API}/billing/cancel`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('ses_token')}`
      }
    });

    if (response.ok) {
      alert('Subscription cancelled successfully.');
      await loadSubscription();
    } else {
      const error = await response.json();
      alert('Error: ' + (error.detail || 'Failed to cancel subscription'));
    }
  } catch (error) {
    logger.error('Error cancelling subscription:', error);
    alert('Error al cancelar la suscripción.');
  }
}

// ═══════════════════════════════════════════════════
// UI UPDATES
// ═══════════════════════════════════════════════════

function updatePlanUI(data) {
  const planBadge = document.getElementById('plan-badge');
  const planName = document.getElementById('plan-name');
  const planLimit = document.getElementById('plan-limit');
  const cancelSection = document.getElementById('cancel-section');

  // Update badge
  planBadge.textContent = data.plan_name.toUpperCase();
  planBadge.className = 'plan-badge' + (data.plan_name.includes('pro') ? ' pro' : '');

  // Update plan name
  const planNames = {
    'free': 'Free Plan',
    'starter': 'Starter Plan',
    'starter_annual': 'Starter Plan (Annual)',
    'pro': 'Pro Plan',
    'pro_annual': 'Pro Plan (Annual)'
  };
  planName.textContent = planNames[data.plan_name] || 'Free Plan';

  // Update limits
  planLimit.textContent = `${data.emails_limit.toLocaleString()} emails/month • ${data.domains_limit === 999 ? 'Unlimited' : data.domains_limit} domains`;

  // Show/hide cancel button
  if (data.plan_name !== 'free') {
    cancelSection.style.display = 'block';
  } else {
    cancelSection.style.display = 'none';
  }

  // Update plan cards
  document.querySelectorAll('.plan-card').forEach(card => {
    const plan = card.dataset.plan;
    if (plan === data.plan_name || plan === data.plan_name.replace('_annual', '')) {
      card.classList.add('current');
    }
  });
}

function updateInvoicesTable(invoices) {
  const tbody = document.getElementById('invoices-body');

  if (!invoices || invoices.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="4" class="empty-state">No invoices yet</td>
      </tr>
    `;
    return;
  }

  tbody.innerHTML = invoices.map(invoice => `
    <tr>
      <td>${formatDate(invoice.created_at)}</td>
      <td>$${invoice.amount.toFixed(2)} ${esc(invoice.currency)}</td>
      <td>
        <span class="invoice-status ${esc(invoice.status)}">${esc(invoice.status)}</span>
      </td>
      <td>
        ${invoice.invoice_url 
          ? `<a href="${esc(invoice.invoice_url)}" target="_blank" class="invoice-link">Download</a>`
          : '-'
        }
      </td>
    </tr>
  `).join('');
}

// ═══════════════════════════════════════════════════
// BILLING TOGGLE
// ═══════════════════════════════════════════════════

function setupBillingToggle() {
  const toggleBtns = document.querySelectorAll('.toggle-btn');
  
  toggleBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      // Update active state
      toggleBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      
      // Update interval
      billingInterval = btn.dataset.interval;
      
      // Update prices
      updatePrices();
    });
  });
}

function updatePrices() {
  document.querySelectorAll('.price-amount').forEach(el => {
    const monthly = el.dataset.monthly;
    const annual = el.dataset.annual;
    el.textContent = billingInterval === 'annual' ? `$${annual}` : `$${monthly}`;
  });
}

// ═══════════════════════════════════════════════════
// UTILS
// ═══════════════════════════════════════════════════

function formatDate(dateStr) {
  const date = new Date(dateStr);
  return date.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric'
  });
}

function getToken() {
  return localStorage.getItem('ses_token');
}
