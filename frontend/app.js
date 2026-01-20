// Configuration
const API_BASE = window.location.hostname === 'localhost' 
    ? 'http://localhost:8000' 
    : 'http://api:8000';

// State management
let authToken = localStorage.getItem('authToken');
let currentUser = null;

// DOM Elements
const loginBtn = document.getElementById('loginBtn');
const logoutBtn = document.getElementById('logoutBtn');
const loginModal = document.getElementById('loginModal');
const loginForm = document.getElementById('loginForm');
const loginError = document.getElementById('loginError');
const closeModal = document.querySelector('.close');

const travelCard = document.getElementById('travelCard');
const assessmentCard = document.getElementById('assessmentCard');
const travelSection = document.getElementById('travelSection');
const assessmentSection = document.getElementById('assessmentSection');
const resultsSection = document.getElementById('resultsSection');
const adminPanel = document.getElementById('adminPanel');

const travelForm = document.getElementById('travelForm');
const assessmentForm = document.getElementById('assessmentForm');
const destinationSelect = document.getElementById('destination');
const loadingOverlay = document.getElementById('loadingOverlay');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    checkAuth();
    loadDestinations();
    setupEventListeners();
});

// Event Listeners
function setupEventListeners() {
    loginBtn.addEventListener('click', () => loginModal.style.display = 'block');
    logoutBtn.addEventListener('click', logout);
    closeModal.addEventListener('click', () => loginModal.style.display = 'none');
    
    window.addEventListener('click', (e) => {
        if (e.target === loginModal) loginModal.style.display = 'none';
    });

    loginForm.addEventListener('submit', handleLogin);
    travelCard.querySelector('button').addEventListener('click', showTravelForm);
    assessmentCard.querySelector('button').addEventListener('click', showAssessmentForm);
    
    document.getElementById('cancelTravel').addEventListener('click', showHome);
    document.getElementById('cancelAssessment').addEventListener('click', showHome);
    document.getElementById('backToHome').addEventListener('click', showHome);
    
    travelForm.addEventListener('submit', handleTravelSubmit);
    assessmentForm.addEventListener('submit', handleAssessmentSubmit);

    // Admin panel
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => switchTab(btn.dataset.tab));
    });

    document.getElementById('vaccineForm').addEventListener('submit', handleVaccineSubmit);
    document.getElementById('caseForm').addEventListener('submit', handleCaseSubmit);
}

// Authentication
// Authentication
async function handleLogin(e) {
    e.preventDefault();
    const username = document.getElementById('username').value.trim();
    const password = document.getElementById('password').value;

    showLoading();
    try {
        const response = await fetch(`${API_BASE}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });

        if (!response.ok) {
            throw new Error('Invalid credentials');
        }

        const data = await response.json();
        authToken = data.access_token;
        localStorage.setItem('authToken', authToken);

        loginModal.style.display = 'none';
        loginForm.reset();
        loginError.classList.remove('show');

        // No /me endpoint anymore; just update UI and open admin panel
        updateAuthUI(true);
        showAdminPanel();

    } catch (error) {
        loginError.textContent = 'Login failed. Please check your credentials.';
        loginError.classList.add('show');
    } finally {
        hideLoading();
    }
}


async function checkAuth() {
  if (!authToken) {
    updateAuthUI(false);
    return;
  }

  try {
    const response = await fetch(`${API_BASE}/resources/vaccines?limit=1`, {
      headers: { 'Authorization': `Bearer ${authToken}` }
    });

    if (response.ok) {
      updateAuthUI(true);
      return;
    }

    // If token invalid/expired
    if (response.status === 401) {
      logout();
      return;
    }

    // For other errors, keep logged out to avoid weird UI state
    logout();
  } catch (e) {
    // If API unreachable, decide behavior:
    // I'd keep user "logged out" to avoid showing admin actions that won't work.
    logout();
  }
}



function updateAuthUI(isAuthenticated) {
    if (isAuthenticated) {
        loginBtn.style.display = 'none';
        logoutBtn.style.display = 'block';
    } else {
        loginBtn.style.display = 'block';
        logoutBtn.style.display = 'none';
        adminPanel.style.display = 'none';
    }
}

function logout() {
    authToken = null;
    currentUser = null;
    localStorage.removeItem('authToken');
    updateAuthUI(false);
    showHome();
}

// Navigation
function showHome() {
    hideAllSections();
    document.querySelector('.service-selection').style.display = 'grid';
}

function showTravelForm() {
    hideAllSections();
    travelSection.style.display = 'block';
}

function showAssessmentForm() {
    hideAllSections();
    assessmentSection.style.display = 'block';
}

function showResults() {
    hideAllSections();
    resultsSection.style.display = 'block';
}

function showAdminPanel() {
    hideAllSections();
    adminPanel.style.display = 'block';
    loadVaccines();
    loadCases();
    loadVaccinesForSelect();
}

function hideAllSections() {
    travelSection.style.display = 'none';
    assessmentSection.style.display = 'none';
    resultsSection.style.display = 'none';
    adminPanel.style.display = 'none';
    document.querySelector('.service-selection').style.display = 'none';
}

function switchTab(tabName) {
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
    
    document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');
    document.getElementById(`${tabName}Tab`).classList.add('active');
}

// API Calls
async function loadDestinations() {
    try {
        const response = await fetch(`${API_BASE}/resources/destinations`);
        const destinations = await response.json();
        
        destinationSelect.innerHTML = '<option value="">Select a destination...</option>';
        destinations.forEach(dest => {
            const option = document.createElement('option');
            option.value = dest.id;
            option.textContent = dest.name;
            destinationSelect.appendChild(option);
        });
    } catch (error) {
        console.error('Failed to load destinations:', error);
        destinationSelect.innerHTML = '<option value="">Failed to load destinations</option>';
    }
}

async function handleTravelSubmit(e) {
    e.preventDefault();
    const destId = destinationSelect.value;
    
    if (!destId) {
        alert('Please select a destination');
        return;
    }

    showLoading();
    try {
        const response = await fetch(`${API_BASE}/resources/destinations/${destId}/recommendations`);
        const data = await response.json();
        
        displayTravelResults(data);
        showResults();
    } catch (error) {
        alert('Failed to fetch recommendations. Please try again.');
        console.error(error);
    } finally {
        hideLoading();
    }
}

async function handleAssessmentSubmit(e) {
    e.preventDefault();
    const problemText = document.getElementById('problemText').value;
    const scenarioType = document.getElementById('scenarioType').value;

    showLoading();
    try {
        const response = await fetch(`${API_BASE}/resources/assessments`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                problem_text: problemText,
                scenario_type: scenarioType || null
            })
        });

        const data = await response.json();
        displayAssessmentResults(data);
        showResults();
        assessmentForm.reset();
    } catch (error) {
        alert('Failed to get assessment. Please try again.');
        console.error(error);
    } finally {
        hideLoading();
    }
}

// Display Results
function displayTravelResults(data) {
    const title = document.getElementById('resultsTitle');
    const content = document.getElementById('resultsContent');
    
    title.textContent = `Vaccine Recommendations for ${data.destination.name}`;
    
    if (data.recommendations.length === 0) {
        content.innerHTML = '<p class="no-results">No specific vaccine recommendations found for this destination.</p>';
        return;
    }

    let html = '';
    data.recommendations.forEach(rec => {
        const statusClass = rec.requirement_level === 'required' ? 'required' : 'recommended';
        const badgeClass = rec.requirement_level === 'required' ? 'badge-required' : 'badge-recommended';
        const availClass = rec.available_in_ipt ? 'badge-available' : 'badge-unavailable';
        
        html += `
            <div class="vaccine-card ${statusClass}">
                <h3>${rec.vaccine_name}</h3>
                <span class="vaccine-badge ${badgeClass}">${rec.requirement_level.toUpperCase()}</span>
                <span class="vaccine-badge ${availClass}">${rec.available_in_ipt ? 'Available at IPT' : 'Not Available'}</span>
                ${rec.price_tnd ? `<div class="price-info">${rec.price_tnd.toFixed(3)} ${rec.currency}</div>` : ''}
                ${rec.notes ? `<p>${rec.notes}</p>` : ''}
            </div>
        `;
    });

    if (data.source_url) {
        html += `<p class="source-info"><small>Source: <a href="${data.source_url}" target="_blank">Pasteur.fr</a></small></p>`;
    }

    content.innerHTML = html;
}

function displayAssessmentResults(data) {
    const title = document.getElementById('resultsTitle');
    const content = document.getElementById('resultsContent');
    
    title.textContent = 'Health Assessment Results';
    
    if (data.matches.length === 0) {
        content.innerHTML = '<p class="no-results">No matching cases found. Please consult a healthcare professional.</p>';
        return;
    }

    let html = '<p style="margin-bottom: 1.5rem;">Based on your description, here are the recommended vaccines:</p>';
    
    data.matches.forEach((match, index) => {
        const scorePercent = (match.score * 100).toFixed(0);
        html += `
            <div class="vaccine-card">
                <h3>${index + 1}. ${match.vaccine_name}</h3>
                ${match.scenario_match ? '<span class="vaccine-badge badge-available">Scenario Match</span>' : ''}
                <p><strong>Similar Case:</strong> ${match.problem_text}</p>
                ${match.vaccine_description ? `<p><small>${match.vaccine_description}</small></p>` : ''}
                <div class="match-score">
                    <span>Match Score:</span>
                    <div class="score-bar">
                        <div class="score-fill" style="width: ${scorePercent}%"></div>
                    </div>
                    <span>${scorePercent}%</span>
                </div>
            </div>
        `;
    });

    html += '<p class="disclaimer" style="margin-top: 1.5rem; padding: 1rem; background: #fef2f2; border-radius: 8px; color: #991b1b;"><strong>Disclaimer:</strong> This is an automated assessment tool for educational purposes. Always consult with a qualified healthcare professional for medical advice.</p>';

    content.innerHTML = html;
}

// Admin Functions
async function loadVaccines() {
    if (!authToken) return;

    try {
        const response = await fetch(`${API_BASE}/resources/vaccines`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        const vaccines = await response.json();
        
        const list = document.getElementById('vaccinesList');
        list.innerHTML = '<h4>Current Vaccines</h4>';
        
        vaccines.forEach(vaccine => {
            const card = document.createElement('div');
            card.className = 'item-card';
            card.innerHTML = `
                <div class="item-info">
                    <h4>${vaccine.name}</h4>
                    <p>${vaccine.description || 'No description'}</p>
                    ${vaccine.price_tnd ? `<p><strong>${vaccine.price_tnd} ${vaccine.currency}</strong></p>` : ''}
                </div>
                <button class="btn-danger" onclick="deleteVaccine(${vaccine.id})">Delete</button>
            `;
            list.appendChild(card);
        });
    } catch (error) {
        console.error('Failed to load vaccines:', error);
    }
}

async function handleVaccineSubmit(e) {
    e.preventDefault();
    if (!authToken) return;

    const data = {
        name: document.getElementById('vaccineName').value,
        description: document.getElementById('vaccineDesc').value || null,
        price_tnd: parseFloat(document.getElementById('vaccinePrice').value) || null
    };

    showLoading();
    try {
        const response = await fetch(`${API_BASE}/resources/vaccines`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${authToken}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });

        if (response.ok) {
            e.target.reset();
            await loadVaccines();
            await loadVaccinesForSelect();
            alert('Vaccine added successfully!');
        } else {
            alert('Failed to add vaccine');
        }
    } catch (error) {
        alert('Error adding vaccine');
        console.error(error);
    } finally {
        hideLoading();
    }
}

async function deleteVaccine(id) {
    if (!confirm('Are you sure you want to delete this vaccine?')) return;
    if (!authToken) return;

    showLoading();
    try {
        const response = await fetch(`${API_BASE}/resources/vaccines/${id}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${authToken}` }
        });

        if (response.ok) {
            await loadVaccines();
            await loadVaccinesForSelect();
            alert('Vaccine deleted successfully!');
        } else {
            alert('Failed to delete vaccine');
        }
    } catch (error) {
        alert('Error deleting vaccine');
        console.error(error);
    } finally {
        hideLoading();
    }
}

async function loadCases() {
    if (!authToken) return;

    try {
        const response = await fetch(`${API_BASE}/resources/cases`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        const cases = await response.json();
        
        const list = document.getElementById('casesList');
        list.innerHTML = '<h4>Current Cases</h4>';
        
        cases.forEach(c => {
            const card = document.createElement('div');
            card.className = 'item-card';
            card.innerHTML = `
                <div class="item-info">
                    <h4>${c.problem_text}</h4>
                    <p>Scenario: ${c.scenario_type || 'N/A'}</p>
                </div>
                <button class="btn-danger" onclick="deleteCase(${c.id})">Delete</button>
            `;
            list.appendChild(card);
        });
    } catch (error) {
        console.error('Failed to load cases:', error);
    }
}

async function loadVaccinesForSelect() {
    try {
        const response = await fetch(`${API_BASE}/resources/vaccines`);
        const vaccines = await response.json();
        
        const select = document.getElementById('caseVaccine');
        select.innerHTML = '<option value="">Select vaccine...</option>';
        vaccines.forEach(v => {
            const option = document.createElement('option');
            option.value = v.id;
            option.textContent = v.name;
            select.appendChild(option);
        });
    } catch (error) {
        console.error('Failed to load vaccines for select:', error);
    }
}

async function handleCaseSubmit(e) {
    e.preventDefault();
    if (!authToken) return;

    const data = {
        problem_text: document.getElementById('caseProblem').value,
        scenario_type: document.getElementById('caseScenario').value || null,
        vaccine_id: parseInt(document.getElementById('caseVaccine').value)
    };

    showLoading();
    try {
        const response = await fetch(`${API_BASE}/resources/cases`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${authToken}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });

        if (response.ok) {
            e.target.reset();
            await loadCases();
            alert('Case added successfully!');
        } else {
            alert('Failed to add case');
        }
    } catch (error) {
        alert('Error adding case');
        console.error(error);
    } finally {
        hideLoading();
    }
}

async function deleteCase(id) {
    if (!confirm('Are you sure you want to delete this case?')) return;
    if (!authToken) return;

    showLoading();
    try {
        const response = await fetch(`${API_BASE}/resources/cases/${id}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${authToken}` }
        });

        if (response.ok) {
            await loadCases();
            alert('Case deleted successfully!');
        } else {
            alert('Failed to delete case');
        }
    } catch (error) {
        alert('Error deleting case');
        console.error(error);
    } finally {
        hideLoading();
    }
}

// Utility Functions
function showLoading() {
    loadingOverlay.style.display = 'flex';
}

function hideLoading() {
    loadingOverlay.style.display = 'none';
}

// Make delete functions available globally
window.deleteVaccine = deleteVaccine;
window.deleteCase = deleteCase;
