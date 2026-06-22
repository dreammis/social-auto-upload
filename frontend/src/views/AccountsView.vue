<template>
  <div class="accounts-page">
    <!-- Header -->
    <div class="page-header">
      <div>
        <h1>Account Manager</h1>
        <p class="subtitle">Manage your social media accounts and cookies</p>
      </div>
      <button class="btn-add" @click="openAddModal">+ Add Account</button>
    </div>

    <!-- Global error -->
    <div v-if="store.error && !showModal" class="error-banner">
      {{ store.error }}
    </div>

    <!-- Table -->
    <div class="table-card">
      <table v-if="store.accounts.length > 0">
        <thead>
          <tr>
            <th>Platform</th>
            <th>Account Name</th>
            <th>Status</th>
            <th>Last Check</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="acc in store.accounts" :key="acc.id">
            <td>
              <span class="platform-badge" :class="`platform-${acc.platform}`">
                {{ platformLabel(acc.platform) }}
              </span>
            </td>
            <td class="account-name">{{ acc.account_name }}</td>
            <td>
              <span class="status-badge" :class="`status-${acc.status}`">
                {{ acc.status }}
              </span>
            </td>
            <td class="health-time">{{ formatDate(acc.last_health_check) }}</td>
            <td class="actions">
              <button class="btn-action btn-ping" @click="handleCheckHealth(acc.id)" title="Check Live">
                ⚡
              </button>
              <button class="btn-action btn-delete" @click="handleDelete(acc.id)" title="Delete">
                🗑
              </button>
            </td>
          </tr>
        </tbody>
      </table>

      <!-- Empty state -->
      <div v-else class="empty-state">
        <div class="empty-icon">👤</div>
        <p>No accounts added yet</p>
        <p class="empty-hint">Click "+ Add Account" to connect your first social media account</p>
      </div>
    </div>

    <!-- Add Account Modal -->
    <div v-if="showModal" class="modal-overlay" @click.self="closeModal">
      <div class="modal">
        <div class="modal-header">
          <h2>Add Account</h2>
          <button class="btn-close" @click="closeModal">✕</button>
        </div>

        <form @submit.prevent="handleSubmit" class="modal-body">
          <div class="form-group">
            <label for="platform">Platform</label>
            <select id="platform" v-model="form.platform" required>
              <option value="" disabled>Select platform...</option>
              <option value="tiktok">TikTok</option>
              <option value="facebook">Facebook</option>
              <option value="youtube">YouTube</option>
              <option value="instagram">Instagram</option>
              <option value="shopee">Shopee</option>
            </select>
          </div>

          <div class="form-group">
            <label for="account_name">Account Name</label>
            <input
              id="account_name"
              v-model="form.account_name"
              type="text"
              required
              placeholder="e.g. My TikTok Creator Account"
            />
          </div>

          <div class="form-group">
            <label for="session_data">Session Data (JSON)</label>
            <textarea
              id="session_data"
              v-model="form.sessionDataRaw"
              rows="6"
              required
              placeholder='Paste your exported cookie/session JSON here&#10;Example: {"cookies": [...], "userAgent": "..."}'
            ></textarea>
            <div v-if="jsonError" class="json-error">
              ⚠️ {{ jsonError }}
            </div>
          </div>

          <div v-if="submitError" class="error-message">
            {{ submitError }}
          </div>

          <div class="modal-actions">
            <button type="button" class="btn-cancel" @click="closeModal">Cancel</button>
            <button type="submit" class="btn-submit" :disabled="isSubmitting || !!jsonError">
              {{ isSubmitting ? 'Adding...' : 'Add Account' }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue';
import { useAccountStore, type Platform } from '@/stores/account.store';

const store = useAccountStore();

// Modal state
const showModal = ref(false);
const isSubmitting = ref(false);
const submitError = ref('');
const jsonError = ref('');

// Form state
const form = ref({
  platform: '' as Platform | '',
  account_name: '',
  sessionDataRaw: '',
});

// Validate JSON on each keystroke
watch(
  () => form.value.sessionDataRaw,
  (raw) => {
    if (!raw.trim()) {
      jsonError.value = '';
      return;
    }
    try {
      JSON.parse(raw);
      jsonError.value = '';
    } catch (e: any) {
      jsonError.value = e.message || 'Invalid JSON';
    }
  },
);

// Platform display labels
function platformLabel(platform: Platform): string {
  const labels: Record<Platform, string> = {
    tiktok: 'TikTok',
    facebook: 'Facebook',
    youtube: 'YouTube',
    instagram: 'Instagram',
    shopee: 'Shopee',
  };
  return labels[platform] || platform;
}

// Format ISO date to relative or local
function formatDate(date: string | null): string {
  if (!date) return '—';
  const d = new Date(date);
  const now = new Date();
  const diffMs = now.getTime() - d.getTime();
  const diffMin = Math.floor(diffMs / 60000);

  if (diffMin < 1) return 'Just now';
  if (diffMin < 60) return `${diffMin}m ago`;
  if (diffMin < 1440) return `${Math.floor(diffMin / 60)}h ago`;
  return d.toLocaleDateString();
}

// --- Modal controls ---
function openAddModal() {
  form.value = { platform: '', account_name: '', sessionDataRaw: '' };
  submitError.value = '';
  jsonError.value = '';
  showModal.value = true;
}

function closeModal() {
  showModal.value = false;
}

// --- Submit: validate JSON, call store ---
async function handleSubmit() {
  submitError.value = '';

  // Validate JSON
  let parsed: Record<string, any>;
  try {
    parsed = JSON.parse(form.value.sessionDataRaw);
  } catch {
    submitError.value = 'Session data is not valid JSON';
    return;
  }

  isSubmitting.value = true;

  const result = await store.addAccount({
    platform: form.value.platform as Platform,
    account_name: form.value.account_name,
    session_data: parsed,
  });

  isSubmitting.value = false;

  if (result.success) {
    closeModal();
  } else {
    submitError.value = result.message || 'Failed to add account';
  }
}

// --- Actions ---
async function handleDelete(id: number) {
  if (!confirm('Delete this account? This cannot be undone.')) return;
  await store.deleteAccount(id);
}

async function handleCheckHealth(id: number) {
  await store.checkHealth(id);
}

// --- Load on mount ---
onMounted(() => {
  store.fetchAccounts();
});
</script>

<style scoped>
.accounts-page {
  max-width: 1100px;
  margin: 0 auto;
}

/* Header */
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;
}

.page-header h1 {
  color: #f1f5f9;
  font-size: 24px;
  margin: 0 0 4px 0;
}

.subtitle {
  color: #64748b;
  font-size: 14px;
  margin: 0;
}

.btn-add {
  padding: 10px 20px;
  background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s;
  white-space: nowrap;
}

.btn-add:hover {
  transform: translateY(-1px);
  box-shadow: 0 8px 20px rgba(59, 130, 246, 0.3);
}

/* Error banner */
.error-banner {
  background: rgba(239, 68, 68, 0.08);
  border: 1px solid rgba(239, 68, 68, 0.2);
  color: #fca5a5;
  padding: 12px 16px;
  border-radius: 8px;
  margin-bottom: 16px;
  font-size: 13px;
}

/* Table card */
.table-card {
  background: rgba(30, 41, 59, 0.6);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(148, 163, 184, 0.08);
  border-radius: 12px;
  overflow: hidden;
}

table {
  width: 100%;
  border-collapse: collapse;
}

thead {
  background: rgba(15, 23, 42, 0.5);
}

th {
  text-align: left;
  padding: 12px 16px;
  color: #64748b;
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

td {
  padding: 14px 16px;
  border-top: 1px solid rgba(148, 163, 184, 0.06);
  color: #e2e8f0;
  font-size: 14px;
}

.account-name {
  font-weight: 500;
}

.health-time {
  color: #64748b;
  font-size: 13px;
}

/* Platform badges */
.platform-badge {
  display: inline-block;
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
}

.platform-tiktok  { background: rgba(0, 0, 0, 0.4); color: #fff;       border: 1px solid rgba(255, 255, 255, 0.2); }
.platform-facebook { background: rgba(24, 119, 242, 0.15); color: #1877F2; border: 1px solid rgba(24, 119, 242, 0.3); }
.platform-youtube  { background: rgba(255, 0, 0, 0.1);   color: #FF0000; border: 1px solid rgba(255, 0, 0, 0.25); }
.platform-instagram{ background: rgba(225, 48, 108, 0.12); color: #E1306C; border: 1px solid rgba(225, 48, 108, 0.3); }
.platform-shopee   { background: rgba(238, 77, 45, 0.12); color: #EE4D2D; border: 1px solid rgba(238, 77, 45, 0.3); }

/* Status badges */
.status-badge {
  display: inline-block;
  padding: 3px 10px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
}

.status-active   { background: rgba(34, 197, 94, 0.12);  color: #22c55e; border: 1px solid rgba(34, 197, 94, 0.3); }
.status-dead     { background: rgba(239, 68, 68, 0.1);   color: #ef4444; border: 1px solid rgba(239, 68, 68, 0.3); }
.status-checking { background: rgba(234, 179, 8, 0.12);  color: #eab308; border: 1px solid rgba(234, 179, 8, 0.3); }

/* Actions */
.actions {
  display: flex;
  gap: 8px;
}

.btn-action {
  width: 32px;
  height: 32px;
  border-radius: 6px;
  border: 1px solid transparent;
  background: transparent;
  cursor: pointer;
  font-size: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s;
}

.btn-ping:hover { background: rgba(234, 179, 8, 0.12);  border-color: rgba(234, 179, 8, 0.3); }
.btn-delete:hover { background: rgba(239, 68, 68, 0.1); border-color: rgba(239, 68, 68, 0.3); }

/* Empty state */
.empty-state {
  text-align: center;
  padding: 60px 20px;
}

.empty-icon {
  font-size: 40px;
  margin-bottom: 12px;
}

.empty-state p {
  color: #94a3b8;
  font-size: 15px;
  margin: 4px 0;
}

.empty-hint {
  font-size: 13px !important;
  color: #64748b !important;
}

/* --- Modal --- */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
}

.modal {
  background: rgba(30, 41, 59, 0.95);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(148, 163, 184, 0.12);
  border-radius: 14px;
  width: 100%;
  max-width: 500px;
  box-shadow: 0 25px 60px rgba(0, 0, 0, 0.6);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  border-bottom: 1px solid rgba(148, 163, 184, 0.08);
}

.modal-header h2 {
  margin: 0;
  color: #f1f5f9;
  font-size: 18px;
}

.btn-close {
  width: 28px;
  height: 28px;
  border: none;
  background: rgba(148, 163, 184, 0.1);
  color: #94a3b8;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.15s;
}

.btn-close:hover {
  background: rgba(239, 68, 68, 0.15);
  color: #fca5a5;
}

.modal-body {
  padding: 24px;
}

.form-group {
  margin-bottom: 20px;
}

.form-group label {
  display: block;
  color: #cbd5e1;
  font-size: 13px;
  font-weight: 500;
  margin-bottom: 6px;
}

.form-group input,
.form-group select,
.form-group textarea {
  width: 100%;
  padding: 10px 14px;
  background: rgba(15, 23, 42, 0.6);
  border: 1px solid rgba(148, 163, 184, 0.15);
  border-radius: 8px;
  color: #f1f5f9;
  font-size: 14px;
  font-family: inherit;
  transition: all 0.15s;
  box-sizing: border-box;
}

.form-group select option {
  background: #1e293b;
  color: #f1f5f9;
}

.form-group input:focus,
.form-group select:focus,
.form-group textarea:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.form-group textarea {
  resize: vertical;
  min-height: 100px;
  font-family: 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.5;
}

/* JSON validation error */
.json-error {
  margin-top: 6px;
  color: #fca5a5;
  font-size: 12px;
  background: rgba(239, 68, 68, 0.08);
  padding: 6px 10px;
  border-radius: 6px;
  border: 1px solid rgba(239, 68, 68, 0.15);
}

/* Submit error */
.error-message {
  background: rgba(239, 68, 68, 0.08);
  border: 1px solid rgba(239, 68, 68, 0.2);
  color: #fca5a5;
  padding: 10px 14px;
  border-radius: 8px;
  margin-bottom: 16px;
  font-size: 13px;
}

/* Modal actions */
.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 24px;
}

.btn-cancel {
  padding: 10px 20px;
  background: rgba(148, 163, 184, 0.08);
  border: 1px solid rgba(148, 163, 184, 0.15);
  color: #94a3b8;
  border-radius: 8px;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.15s;
}

.btn-cancel:hover {
  background: rgba(148, 163, 184, 0.15);
  color: #e2e8f0;
}

.btn-submit {
  padding: 10px 20px;
  background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s;
}

.btn-submit:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 8px 20px rgba(59, 130, 246, 0.3);
}

.btn-submit:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
