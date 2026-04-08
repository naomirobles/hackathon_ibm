import { cn } from "@/lib/utils";

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "outline" | "danger" | "ghost";
  size?: "sm" | "md" | "lg";
}

export function Button({ variant = "primary", size = "md", className, children, ...props }: ButtonProps) {
  const baseStyles = "inline-flex items-center justify-center font-medium rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed";
  
  const variants = {
    primary: "bg-[#2D5A3D] text-white hover:bg-[#4A8C62] focus:ring-[#2D5A3D]",
    secondary: "bg-[#1A4A7A] text-white hover:bg-blue-800 focus:ring-[#1A4A7A]",
    outline: "border border-gray-300 bg-transparent text-gray-700 hover:bg-gray-50 focus:ring-gray-500",
    danger: "bg-[#C0392B] text-white hover:bg-red-700 focus:ring-[#C0392B]",
    ghost: "bg-transparent text-gray-600 hover:bg-gray-100 hover:text-gray-900 focus:ring-gray-500",
  };

  const sizes = {
    sm: "px-3 py-1.5 text-sm gap-1.5",
    md: "px-5 py-2.5 text-sm gap-2",
    lg: "px-6 py-3 text-base gap-2.5",
  };

  return (
    <button className={cn(baseStyles, variants[variant], sizes[size], className)} {...props}>
      {children}
    </button>
  );
}
