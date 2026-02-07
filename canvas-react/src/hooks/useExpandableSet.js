import { useState, useCallback } from 'react';

/**
 * Custom hook for managing a set of expanded items (e.g., expandable table rows)
 * @param {Set<any>} initialExpanded - Initial set of expanded items
 * @returns {Object} - { expandedSet, toggleExpanded }
 */
export function useExpandableSet(initialExpanded = new Set()) {
  const [expandedSet, setExpandedSet] = useState(initialExpanded);

  const toggleExpanded = useCallback((id) => {
    setExpandedSet(prev => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }, []);

  return { expandedSet, toggleExpanded };
}
