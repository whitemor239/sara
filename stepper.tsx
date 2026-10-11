import * as React from "react";
import { Check, ChevronLeft, ChevronRight } from "lucide-react";

export interface StepItem {
  id: string | number;
  title: string;
  description?: string;
}

export interface StepperProps {
  steps: StepItem[];
  currentStep: number; // 0-indexed
  onStepChange?: (index: number) => void;
  allowClickPrevious?: boolean;
  className?: string;
}

const FA_DIGITS = ["۰", "۱", "۲", "۳", "۴", "۵", "۶", "۷", "۸", "۹"];

export function toPersianDigits(n: number | string): string {
  return String(n).replace(/\d/g, (d) => FA_DIGITS[Number(d)] ?? d);
}

export function Stepper({
  steps,
  currentStep,
  onStepChange,
  allowClickPrevious = true,
  className = "",
}: StepperProps) {
  const isInteractive = (index: number) => {
    if (!onStepChange) return false;
    if (allowClickPrevious) return index < currentStep;
    return false;
  };

  return (
    <nav
      dir="rtl"
      aria-label="مراحل فرایند"
      className={`w-full font-['Vazirmatn','Vazir',sans-serif] ${className}`}
    >
      <ol className="flex items-center w-full">
        {steps.map((step, index) => {
          const isCompleted = index < currentStep;
          const isCurrent = index === currentStep;
          const isUpcoming = index > currentStep;
          const isClickable = isInteractive(index);
          const isLast = index === steps.length - 1;

          return (
            <li
              key={step.id}
              className={`flex items-center ${isLast ? "flex-none" : "flex-1"}`}
            >
              <div className="flex flex-col items-center gap-2">
                <button
                  type="button"
                  disabled={!isClickable}
                  onClick={() => isClickable && onStepChange?.(index)}
                  aria-current={isCurrent ? "step" : undefined}
                  aria-label={`مرحله ${toPersianDigits(index + 1)}: ${step.title}`}
                  className={`
                    relative flex h-10 w-10 items-center justify-center rounded-full
                    transition-all duration-200 motion-reduce:transition-none
                    outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background
                    ${isClickable ? "cursor-pointer hover:opacity-90 active:scale-95" : "cursor-default"}
                    ${
                      isCompleted
                        ? "bg-primary text-primary-foreground shadow-sm"
                        : isCurrent
                        ? "border-2 border-primary bg-background text-primary ring-4 ring-primary/20"
                        : "border-2 border-border bg-muted/40 text-muted-foreground"
                    }
                  `}
                >
                  {isCompleted ? (
                    <Check
                      className="h-5 w-5 stroke-[2.5]"
                      aria-hidden="true"
                    />
                  ) : (
                    <span className="text-sm font-semibold select-none">
                      {toPersianDigits(index + 1)}
                    </span>
                  )}
                </button>

                <div className="flex flex-col items-center text-center">
                  <span
                    className={`text-xs font-medium md:text-sm select-none ${
                      isCurrent
                        ? "text-foreground font-bold"
                        : isCompleted
                        ? "text-foreground"
                        : "text-muted-foreground"
                    }`}
                  >
                    {step.title}
                  </span>
                  {step.description && (
                    <span className="hidden md:inline-block text-[11px] text-muted-foreground mt-0.5 max-w-[120px] truncate select-none">
                      {step.description}
                    </span>
                  )}
                </div>
              </div>

              {!isLast && (
                <div
                  aria-hidden="true"
                  className="flex-1 mx-2 sm:mx-4 mb-6"
                >
                  <div
                    className={`h-0.5 w-full transition-colors duration-200 motion-reduce:transition-none ${
                      index < currentStep ? "bg-primary" : "bg-border"
                    }`}
                  />
                </div>
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}

// -----------------------------------------------------------------------------
// مثال استفاده (Usage Example)
// -----------------------------------------------------------------------------
export function StepperExample() {
  const [currentStep, setCurrentStep] = React.useState(1);

  const steps: StepItem[] = [
    { id: "basket", title: "سبد خرید", description: "بررسی اقلام" },
    { id: "shipping", title: "اطلاعات ارسال", description: "نشانی و زمان" },
    { id: "payment", title: "پرداخت نهایی", description: "درگاه بانکی" },
  ];

  return (
    <div dir="rtl" className="max-w-2xl mx-auto p-6 space-y-8 bg-background text-foreground">
      <Stepper
        steps={steps}
        currentStep={currentStep}
        onStepChange={setCurrentStep}
      />

      <div className="rounded-lg border border-border p-6 bg-card text-card-foreground">
        <p className="text-sm text-muted-foreground">
          مرحله فعلی: <span className="font-bold text-foreground">{steps[currentStep].title}</span>
        </p>
        <p className="text-xs text-muted-foreground mt-1">
          مبلغ قابل پرداخت: {toPersianDigits("۲۴۵٬۰۰۰")} تومان
        </p>
      </div>

      <div className="flex justify-between items-center pt-4">
        <button
          type="button"
          disabled={currentStep === 0}
          onClick={() => setCurrentStep((s) => Math.max(0, s - 1))}
          className="inline-flex items-center gap-1.5 px-4 py-2 text-sm font-medium rounded-md border border-border bg-background text-foreground disabled:opacity-50 disabled:cursor-not-allowed hover:bg-muted transition-colors duration-150 motion-reduce:transition-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          {/* آیکون قبلی در چیدمان راست‌به‌چپ به سمت راست اشاره می‌کند */}
          <ChevronRight className="h-4 w-4" aria-hidden="true" />
          <span>مرحله قبل</span>
        </button>

        <button
          type="button"
          disabled={currentStep === steps.length - 1}
          onClick={() => setCurrentStep((s) => Math.min(steps.length - 1, s + 1))}
          className="inline-flex items-center gap-1.5 px-4 py-2 text-sm font-medium rounded-md bg-primary text-primary-foreground disabled:opacity-50 disabled:cursor-not-allowed hover:bg-primary/90 transition-colors duration-150 motion-reduce:transition-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          <span>مرحله بعد</span>
          {/* آیکون بعدی در چیدمان راست‌به‌چپ به سمت چپ اشاره می‌کند */}
          <ChevronLeft className="h-4 w-4" aria-hidden="true" />
        </button>
      </div>
    </div>
  );
}
