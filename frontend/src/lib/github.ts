// Base URL for fetching markdown from GitHub raw
const REPO = "arymax/daily-finance-report";
const BRANCH = "main";

export const rawUrl = (path: string) =>
  `https://raw.githubusercontent.com/${REPO}/${BRANCH}/docs/${path}`;
