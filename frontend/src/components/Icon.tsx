import { ICON_PATHS } from "@/components/icons/paths";

type Props = {
  name: string;
  className?: string;
  size?: number;
};

export function Icon({ name, className = "", size = 20 }: Props) {
  const paths = ICON_PATHS[name];
  if (!paths) return null;

  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.75}
      className={`mf-icon ${className}`.trim()}
      aria-hidden
    >
      {paths}
    </svg>
  );
}
