import { cn } from "@/lib/utils";

interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: "alta" | "media" | "baja" | "info" | "default";
}

export function Badge({ variant = "default", className, children, ...props }: BadgeProps) {
  const variants = {
    alta: "bg-[#FBEAE8] text-[#C0392B]",
    media: "bg-[#FDF3E7] text-[#B7610A]",
    baja: "bg-[#E8F2EC] text-[#2D5A3D]",
    info: "bg-[#E8F0FA] text-[#1A4A7A]",
    default: "bg-gray-100 text-gray-700",
  };

  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold uppercase tracking-wider",
        variants[variant],
        className
      )}
      {...props}
    >
      {children}
    </span>
  );
}
