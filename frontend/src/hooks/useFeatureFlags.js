/**
 * Feature flags hook - Community Edition
 *
 * In the Community edition, all core features are unlocked.
 * PRO/Enterprise tier detection is available in FilaOps Pro.
 */
export const useFeatureFlags = () => {
  return {
    tier: 'community',
    features: [],
    hasFeature: () => false,
    isPro: false,
    isEnterprise: false,
    loading: false,
  };
};
