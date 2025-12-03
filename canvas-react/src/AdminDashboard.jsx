import React, { useState, useEffect, useCallback } from 'react';
import { Shield, RefreshCw, Trash2, Key, Copy, X, AlertCircle, CheckCircle, UserPlus } from 'lucide-react';

const AdminDashboard = ({ backendUrl, getAuthHeaders }) => {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [lastUpdated, setLastUpdated] = useState(null);

  // Modal states
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [showResetModal, setShowResetModal] = useState(false);
  const [showAddUserModal, setShowAddUserModal] = useState(false);
  const [selectedUser, setSelectedUser] = useState(null);
  const [newPassword, setNewPassword] = useState('');
  const [copied, setCopied] = useState(false);

  // Add user form state
  const [newUserEmail, setNewUserEmail] = useState('');
  const [newUserName, setNewUserName] = useState('');
  const [newUserRole, setNewUserRole] = useState('ta');
  const [generatedPassword, setGeneratedPassword] = useState('');

  // Action loading states
  const [actionLoading, setActionLoading] = useState(false);
  const [actionError, setActionError] = useState('');

  const loadUsers = useCallback(async () => {
    setLoading(true);
    setError('');

    try {
      const headers = getAuthHeaders();
      const response = await fetch(`${backendUrl}/api/admin/users`, { headers });

      if (!response.ok) {
        if (response.status === 403) {
          throw new Error('Admin access required. You do not have permission to view this page.');
        }
        throw new Error(`Failed to load users: ${response.statusText}`);
      }

      const data = await response.json();
      setUsers(data.users || []);
      setLastUpdated(new Date(data.timestamp));
    } catch (err) {
      console.error('Error loading users:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [backendUrl, getAuthHeaders]);

  useEffect(() => {
    loadUsers();
  }, [loadUsers]);

  const handleDeleteClick = (user) => {
    setSelectedUser(user);
    setShowDeleteModal(true);
    setActionError('');
  };

  const handleDeleteConfirm = async () => {
    setActionLoading(true);
    setActionError('');

    try {
      const headers = getAuthHeaders();
      const response = await fetch(`${backendUrl}/api/admin/users`, {
        method: 'DELETE',
        headers,
        body: JSON.stringify({ email: selectedUser.email })
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Failed to delete user');
      }

      // Reload users and close modal
      await loadUsers();
      setShowDeleteModal(false);
      setSelectedUser(null);
    } catch (err) {
      console.error('Error deleting user:', err);
      setActionError(err.message);
    } finally {
      setActionLoading(false);
    }
  };

  const handleResetPasswordClick = (user) => {
    setSelectedUser(user);
    setShowResetModal(true);
    setNewPassword('');
    setCopied(false);
    setActionError('');
  };

  const handleResetPasswordConfirm = async () => {
    setActionLoading(true);
    setActionError('');

    try {
      const headers = getAuthHeaders();
      const response = await fetch(`${backendUrl}/api/admin/users/reset-password`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ email: selectedUser.email })
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Failed to reset password');
      }

      setNewPassword(data.new_password);
    } catch (err) {
      console.error('Error resetting password:', err);
      setActionError(err.message);
    } finally {
      setActionLoading(false);
    }
  };

  const handleCopyPassword = () => {
    navigator.clipboard.writeText(newPassword);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const closeDeleteModal = () => {
    if (!actionLoading) {
      setShowDeleteModal(false);
      setSelectedUser(null);
      setActionError('');
    }
  };

  const closeResetModal = () => {
    if (!actionLoading) {
      setShowResetModal(false);
      setSelectedUser(null);
      setNewPassword('');
      setCopied(false);
      setActionError('');
    }
  };

  const handleAddUserClick = () => {
    setShowAddUserModal(true);
    setNewUserEmail('');
    setNewUserName('');
    setNewUserRole('ta');
    setGeneratedPassword('');
    setCopied(false);
    setActionError('');
  };

  const handleAddUserConfirm = async () => {
    setActionLoading(true);
    setActionError('');

    try {
      const headers = getAuthHeaders();
      const response = await fetch(`${backendUrl}/api/admin/users/create`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          email: newUserEmail,
          name: newUserName,
          role: newUserRole
        })
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Failed to create user');
      }

      setGeneratedPassword(data.generated_password);

      // Reload users list
      await loadUsers();
    } catch (err) {
      console.error('Error creating user:', err);
      setActionError(err.message);
    } finally {
      setActionLoading(false);
    }
  };

  const closeAddUserModal = () => {
    if (!actionLoading) {
      setShowAddUserModal(false);
      setNewUserEmail('');
      setNewUserName('');
      setNewUserRole('ta');
      setGeneratedPassword('');
      setCopied(false);
      setActionError('');
    }
  };

  const handleCopyGeneratedPassword = () => {
    navigator.clipboard.writeText(generatedPassword);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const formatDate = (dateString) => {
    try {
      return new Date(dateString).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch {
      return dateString;
    }
  };

  const getRoleBadgeClasses = (role) => {
    if (role === 'admin') {
      return 'bg-purple-100 text-purple-800 border-purple-300';
    }
    return 'bg-blue-100 text-blue-800 border-blue-300';
  };

  if (error && !users.length) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="bg-red-50 border-2 border-red-200 rounded-lg p-6">
          <div className="flex items-start">
            <AlertCircle className="h-6 w-6 text-red-600 mr-3 flex-shrink-0 mt-0.5" />
            <div>
              <h3 className="text-lg font-semibold text-red-900 mb-2">Error Loading Admin Dashboard</h3>
              <p className="text-red-700">{error}</p>
              <button
                onClick={loadUsers}
                className="mt-4 px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 transition-colors"
              >
                Try Again
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Shield className="h-8 w-8 text-purple-600" />
            <h1 className="text-2xl font-bold text-gray-900">Admin Dashboard</h1>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={handleAddUserClick}
              className="inline-flex items-center px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 transition-colors"
            >
              <UserPlus className="h-4 w-4 mr-2" />
              Add User
            </button>
            <button
              onClick={loadUsers}
              disabled={loading}
              className="inline-flex items-center px-4 py-2 bg-purple-600 text-white rounded-md hover:bg-purple-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
            >
              <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
              Refresh
            </button>
          </div>
        </div>
        {lastUpdated && (
          <p className="text-sm text-gray-500 mt-2">
            Last updated: {formatDate(lastUpdated)}
          </p>
        )}
      </div>

      {/* User Management Table */}
      <div className="bg-white border border-gray-200 rounded-lg shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200 bg-gray-50">
          <h2 className="text-lg font-semibold text-gray-900">User Management</h2>
          <p className="text-sm text-gray-600 mt-1">
            {users.length} {users.length === 1 ? 'user' : 'users'} total
          </p>
        </div>

        {loading && !users.length ? (
          <div className="px-6 py-12 text-center">
            <RefreshCw className="h-8 w-8 animate-spin mx-auto text-purple-600 mb-4" />
            <p className="text-gray-600">Loading users...</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Email
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Name
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Role
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Created
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {users.map((user) => (
                  <tr key={user.email} className="hover:bg-gray-50 transition-colors">
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                      {user.email}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700">
                      {user.name}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${getRoleBadgeClasses(user.role)}`}>
                        {user.role === 'admin' && <Shield className="w-3 h-3 mr-1" />}
                        {user.role.toUpperCase()}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                      {formatDate(user.created_at)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                      <button
                        onClick={() => handleResetPasswordClick(user)}
                        className="inline-flex items-center px-3 py-1.5 bg-blue-50 text-blue-700 rounded-md hover:bg-blue-100 transition-colors mr-2"
                        title="Reset Password"
                      >
                        <Key className="h-4 w-4 mr-1" />
                        Reset
                      </button>
                      <button
                        onClick={() => handleDeleteClick(user)}
                        className="inline-flex items-center px-3 py-1.5 bg-red-50 text-red-700 rounded-md hover:bg-red-100 transition-colors"
                        title="Delete User"
                      >
                        <Trash2 className="h-4 w-4 mr-1" />
                        Delete
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Delete Confirmation Modal */}
      {showDeleteModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl max-w-md w-full">
            <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
              <h3 className="text-lg font-semibold text-gray-900">Confirm Delete</h3>
              <button
                onClick={closeDeleteModal}
                disabled={actionLoading}
                className="text-gray-400 hover:text-gray-600 disabled:cursor-not-allowed"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="px-6 py-4">
              {actionError && (
                <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-md flex items-start">
                  <AlertCircle className="h-5 w-5 text-red-600 mr-2 flex-shrink-0 mt-0.5" />
                  <p className="text-sm text-red-700">{actionError}</p>
                </div>
              )}

              <div className="bg-amber-50 border border-amber-200 rounded-md p-4 mb-4">
                <div className="flex items-start">
                  <AlertCircle className="h-5 w-5 text-amber-600 mr-2 flex-shrink-0 mt-0.5" />
                  <p className="text-sm text-amber-800">
                    Are you sure you want to delete this user? This action cannot be undone.
                  </p>
                </div>
              </div>

              {selectedUser && (
                <div className="bg-gray-50 rounded-md p-4 mb-4">
                  <p className="text-sm text-gray-600 mb-1">Email:</p>
                  <p className="text-sm font-medium text-gray-900 mb-3">{selectedUser.email}</p>
                  <p className="text-sm text-gray-600 mb-1">Name:</p>
                  <p className="text-sm font-medium text-gray-900">{selectedUser.name}</p>
                </div>
              )}
            </div>

            <div className="px-6 py-4 bg-gray-50 border-t border-gray-200 flex justify-end gap-3 rounded-b-lg">
              <button
                onClick={closeDeleteModal}
                disabled={actionLoading}
                className="px-4 py-2 text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:cursor-not-allowed transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleDeleteConfirm}
                disabled={actionLoading}
                className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors inline-flex items-center"
              >
                {actionLoading && <RefreshCw className="h-4 w-4 mr-2 animate-spin" />}
                {actionLoading ? 'Deleting...' : 'Delete User'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Reset Password Modal */}
      {showResetModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl max-w-md w-full">
            <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
              <h3 className="text-lg font-semibold text-gray-900">Reset Password</h3>
              <button
                onClick={closeResetModal}
                disabled={actionLoading}
                className="text-gray-400 hover:text-gray-600 disabled:cursor-not-allowed"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="px-6 py-4">
              {actionError && (
                <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-md flex items-start">
                  <AlertCircle className="h-5 w-5 text-red-600 mr-2 flex-shrink-0 mt-0.5" />
                  <p className="text-sm text-red-700">{actionError}</p>
                </div>
              )}

              {selectedUser && (
                <div className="bg-gray-50 rounded-md p-4 mb-4">
                  <p className="text-sm text-gray-600 mb-1">User:</p>
                  <p className="text-sm font-medium text-gray-900 mb-2">{selectedUser.name}</p>
                  <p className="text-sm text-gray-600 mb-1">Email:</p>
                  <p className="text-sm font-medium text-gray-900">{selectedUser.email}</p>
                </div>
              )}

              {!newPassword ? (
                <div className="bg-blue-50 border border-blue-200 rounded-md p-4 mb-4">
                  <p className="text-sm text-blue-800">
                    A new secure password will be generated. You must save and share it with the user immediately.
                  </p>
                </div>
              ) : (
                <div>
                  <div className="bg-green-50 border border-green-200 rounded-md p-4 mb-4">
                    <div className="flex items-start">
                      <CheckCircle className="h-5 w-5 text-green-600 mr-2 flex-shrink-0 mt-0.5" />
                      <p className="text-sm text-green-800">
                        Password reset successfully! Copy and share this password securely with the user.
                      </p>
                    </div>
                  </div>

                  <div className="bg-gray-900 text-white rounded-md p-4 font-mono text-sm mb-3 flex items-center justify-between">
                    <span className="break-all">{newPassword}</span>
                    <button
                      onClick={handleCopyPassword}
                      className="ml-3 p-2 bg-gray-700 hover:bg-gray-600 rounded-md transition-colors flex-shrink-0"
                      title="Copy to clipboard"
                    >
                      {copied ? (
                        <CheckCircle className="h-4 w-4 text-green-400" />
                      ) : (
                        <Copy className="h-4 w-4" />
                      )}
                    </button>
                  </div>

                  <div className="bg-amber-50 border border-amber-200 rounded-md p-3">
                    <p className="text-xs text-amber-800">
                      <strong>Warning:</strong> This password will only be shown once. Make sure to save it before closing this window.
                    </p>
                  </div>
                </div>
              )}
            </div>

            <div className="px-6 py-4 bg-gray-50 border-t border-gray-200 flex justify-end gap-3 rounded-b-lg">
              {!newPassword ? (
                <>
                  <button
                    onClick={closeResetModal}
                    disabled={actionLoading}
                    className="px-4 py-2 text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:cursor-not-allowed transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleResetPasswordConfirm}
                    disabled={actionLoading}
                    className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors inline-flex items-center"
                  >
                    {actionLoading && <RefreshCw className="h-4 w-4 mr-2 animate-spin" />}
                    {actionLoading ? 'Generating...' : 'Reset Password'}
                  </button>
                </>
              ) : (
                <button
                  onClick={closeResetModal}
                  className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
                >
                  Done
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Add User Modal */}
      {showAddUserModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl max-w-md w-full">
            <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
              <h3 className="text-lg font-semibold text-gray-900">Add New User</h3>
              <button
                onClick={closeAddUserModal}
                disabled={actionLoading}
                className="text-gray-400 hover:text-gray-600 disabled:cursor-not-allowed"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="px-6 py-4">
              {actionError && (
                <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-md flex items-start">
                  <AlertCircle className="h-5 w-5 text-red-600 mr-2 flex-shrink-0 mt-0.5" />
                  <p className="text-sm text-red-700">{actionError}</p>
                </div>
              )}

              {!generatedPassword ? (
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Email Address *
                    </label>
                    <input
                      type="email"
                      value={newUserEmail}
                      onChange={(e) => setNewUserEmail(e.target.value)}
                      placeholder="user@gatech.edu"
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-green-500 focus:border-green-500"
                      disabled={actionLoading}
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Full Name *
                    </label>
                    <input
                      type="text"
                      value={newUserName}
                      onChange={(e) => setNewUserName(e.target.value)}
                      placeholder="John Doe"
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-green-500 focus:border-green-500"
                      disabled={actionLoading}
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Role *
                    </label>
                    <select
                      value={newUserRole}
                      onChange={(e) => setNewUserRole(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-green-500 focus:border-green-500"
                      disabled={actionLoading}
                    >
                      <option value="ta">TA</option>
                      <option value="admin">Admin</option>
                    </select>
                  </div>

                  <div className="bg-blue-50 border border-blue-200 rounded-md p-3">
                    <p className="text-sm text-blue-800">
                      A secure password will be automatically generated for this user.
                    </p>
                  </div>
                </div>
              ) : (
                <div>
                  <div className="bg-green-50 border border-green-200 rounded-md p-4 mb-4">
                    <div className="flex items-start">
                      <CheckCircle className="h-5 w-5 text-green-600 mr-2 flex-shrink-0 mt-0.5" />
                      <p className="text-sm text-green-800">
                        User created successfully! Copy this password and share it securely with the user.
                      </p>
                    </div>
                  </div>

                  <div className="mb-3">
                    <p className="text-sm font-medium text-gray-700 mb-2">Generated Password:</p>
                    <div className="bg-gray-900 text-white rounded-md p-4 font-mono text-sm flex items-center justify-between">
                      <span className="break-all">{generatedPassword}</span>
                      <button
                        onClick={handleCopyGeneratedPassword}
                        className="ml-3 p-2 bg-gray-700 hover:bg-gray-600 rounded-md transition-colors flex-shrink-0"
                        title="Copy to clipboard"
                      >
                        {copied ? (
                          <CheckCircle className="h-4 w-4 text-green-400" />
                        ) : (
                          <Copy className="h-4 w-4" />
                        )}
                      </button>
                    </div>
                  </div>

                  <div className="bg-amber-50 border border-amber-200 rounded-md p-3">
                    <p className="text-xs text-amber-800">
                      <strong>Warning:</strong> This password will only be shown once. Make sure to save it before closing this window.
                    </p>
                  </div>
                </div>
              )}
            </div>

            <div className="px-6 py-4 bg-gray-50 border-t border-gray-200 flex justify-end gap-3 rounded-b-lg">
              {!generatedPassword ? (
                <>
                  <button
                    onClick={closeAddUserModal}
                    disabled={actionLoading}
                    className="px-4 py-2 text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:cursor-not-allowed transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleAddUserConfirm}
                    disabled={actionLoading || !newUserEmail || !newUserName}
                    className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors inline-flex items-center"
                  >
                    {actionLoading && <RefreshCw className="h-4 w-4 mr-2 animate-spin" />}
                    {actionLoading ? 'Creating...' : 'Create User'}
                  </button>
                </>
              ) : (
                <button
                  onClick={closeAddUserModal}
                  className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 transition-colors"
                >
                  Done
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AdminDashboard;
