export default function LogoPlaceholder({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 100 100"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
    >
      <path
        d="M50 10L90 30V70L50 90L10 70V30L50 10Z"
        stroke="currentColor"
        strokeWidth="6"
        strokeLinejoin="round"
      />
      <circle cx="50" cy="50" r="15" fill="currentColor" />
    </svg>
  );
}
