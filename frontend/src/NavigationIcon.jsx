export default function NavigationIcon({name}) {
  const paths = {
    screen: <><path d="M8 4H5v16h14V4h-3M9 3h6v4H9z"/><path d="M8 12h8m-8 4h5"/></>,
    rules: <><path d="M4 6h16M4 12h16M4 18h16"/><path d="M8 3v6m8 0v6m-8 0v6"/></>,
    history: <><path d="M3 11a9 9 0 1 1 2 7M3 4v7h7"/><path d="M12 7v5l3 2"/></>,
    collapse: <><rect x="3" y="4" width="18" height="16" rx="1"/><path d="M9 4v16m7-12-4 4 4 4"/></>,
    expand: <><rect x="3" y="4" width="18" height="16" rx="1"/><path d="M9 4v16m4-12 4 4-4 4"/></>,
    account: <><circle cx="12" cy="8" r="3"/><path d="M5 21v-2a7 7 0 0 1 14 0v2"/></>,
  };
  return <svg className="navigation-icon" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" focusable="false">{paths[name]}</svg>;
}
