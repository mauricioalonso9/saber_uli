import { zodResolver } from "@hookform/resolvers/zod";
import { useId, useMemo } from "react";
import { useForm } from "react-hook-form";
import { useTranslation } from "react-i18next";
import { z } from "zod";

import type { Me, Profile, ProfileUpdate, ProfileUpdateDailyGoal, Program } from "@/api/model";
import { Button } from "@/shared/ui/button";
import { Input } from "@/shared/ui/input";
import { Label } from "@/shared/ui/label";

const GOALS: ProfileUpdateDailyGoal[] = ["casual", "regular", "intense"];
const SEMESTERS = Array.from({ length: 12 }, (_, index) => String(index + 1));

interface ProfileFormValues {
  program_id: string;
  semester: string;
  expected_exam_date: string;
  daily_goal: ProfileUpdateDailyGoal;
  guest_display_name: string;
}

function useSchema(kind: Me["kind"]) {
  const { t } = useTranslation();
  return useMemo(() => {
    const goal = z.enum(["casual", "regular", "intense"]);
    if (kind === "guest") {
      return z.object({
        program_id: z.string(),
        semester: z.string(),
        expected_exam_date: z.string(),
        daily_goal: goal,
        guest_display_name: z
          .string()
          .trim()
          .min(2, t("profile.errors.guestName"))
          .max(120, t("profile.errors.guestName")),
      });
    }
    return z.object({
      program_id: z.string().min(1, t("profile.errors.program")),
      semester: z.string().min(1, t("profile.errors.semester")),
      expected_exam_date: z.string().min(1, t("profile.errors.examDate")),
      daily_goal: goal,
      guest_display_name: z.string(),
    });
  }, [kind, t]);
}

function toUpdate(kind: Me["kind"], values: ProfileFormValues): ProfileUpdate {
  if (kind === "guest") {
    return {
      guest_display_name: values.guest_display_name.trim(),
      daily_goal: values.daily_goal,
      ...(values.expected_exam_date ? { expected_exam_date: values.expected_exam_date } : {}),
    };
  }
  return {
    program_id: values.program_id,
    semester: Number(values.semester),
    expected_exam_date: values.expected_exam_date,
    daily_goal: values.daily_goal,
  };
}

interface ProfileFormProps {
  kind: Me["kind"];
  profile: Profile;
  programs: Program[];
  /** Id del título que nombra el formulario. */
  labelledBy: string;
  submitLabel: string;
  pending: boolean;
  onSubmit: (update: ProfileUpdate) => void | Promise<void>;
}

/**
 * Campos del perfil según el tipo de cuenta (FR-019, FR-020). Cada error queda en su campo con
 * `aria-invalid` y `aria-describedby`, y el foco va al primer campo con error.
 */
export function ProfileForm({
  kind,
  profile,
  programs,
  labelledBy,
  submitLabel,
  pending,
  onSubmit,
}: ProfileFormProps) {
  const { t } = useTranslation();
  const ids = {
    program: useId(),
    semester: useId(),
    examDate: useId(),
    goal: useId(),
    name: useId(),
  };
  const form = useForm<ProfileFormValues>({
    resolver: zodResolver(useSchema(kind)),
    defaultValues: {
      program_id: profile.program?.id ?? "",
      semester: profile.semester ? String(profile.semester) : "",
      expected_exam_date: profile.expected_exam_date ?? "",
      daily_goal: profile.daily_goal,
      guest_display_name: profile.guest_display_name ?? "",
    },
  });
  const { errors } = form.formState;

  const describedBy = (id: string, failed: boolean) => (failed ? `${id}-error` : undefined);
  const fieldError = (id: string, message?: string) =>
    message ? (
      <p id={`${id}-error`} className="mt-1 text-sm text-destructive">
        {message}
      </p>
    ) : null;

  // Un programa inactivo que la persona ya tenía sigue apareciendo para poder conservarlo.
  const options =
    profile.program && !programs.some((program) => program.id === profile.program?.id)
      ? [...programs, profile.program]
      : programs;

  return (
    <form
      aria-labelledby={labelledBy}
      noValidate
      onSubmit={(event) =>
        void form.handleSubmit((values) => onSubmit(toUpdate(kind, values)))(event)
      }
      className="flex flex-col gap-5"
    >
      {kind === "guest" ? (
        <div>
          <Label htmlFor={ids.name}>{t("profile.guestName")}</Label>
          <Input
            id={ids.name}
            autoComplete="name"
            maxLength={120}
            aria-invalid={errors.guest_display_name ? true : undefined}
            aria-describedby={describedBy(ids.name, Boolean(errors.guest_display_name))}
            {...form.register("guest_display_name")}
          />
          {fieldError(ids.name, errors.guest_display_name?.message)}
        </div>
      ) : (
        <>
          <div>
            <Label htmlFor={ids.program}>{t("profile.program")}</Label>
            <select
              id={ids.program}
              className="mt-1 h-11 w-full rounded-md border border-input bg-background px-3"
              aria-invalid={errors.program_id ? true : undefined}
              aria-describedby={describedBy(ids.program, Boolean(errors.program_id))}
              {...form.register("program_id")}
            >
              <option value="">{t("profile.chooseProgram")}</option>
              {options.map((program) => (
                <option key={program.id} value={program.id}>
                  {`${program.name} (${program.campus})`}
                </option>
              ))}
            </select>
            {fieldError(ids.program, errors.program_id?.message)}
          </div>
          <div>
            <Label htmlFor={ids.semester}>{t("profile.semester")}</Label>
            <select
              id={ids.semester}
              className="mt-1 h-11 w-full rounded-md border border-input bg-background px-3"
              aria-invalid={errors.semester ? true : undefined}
              aria-describedby={describedBy(ids.semester, Boolean(errors.semester))}
              {...form.register("semester")}
            >
              <option value="">{t("profile.chooseSemester")}</option>
              {SEMESTERS.map((semester) => (
                <option key={semester} value={semester}>
                  {semester}
                </option>
              ))}
            </select>
            {fieldError(ids.semester, errors.semester?.message)}
          </div>
        </>
      )}

      <div>
        <Label htmlFor={ids.examDate}>
          {kind === "guest" ? t("profile.examDateOptional") : t("profile.examDate")}
        </Label>
        <Input
          id={ids.examDate}
          type="date"
          className="h-11"
          aria-invalid={errors.expected_exam_date ? true : undefined}
          aria-describedby={describedBy(ids.examDate, Boolean(errors.expected_exam_date))}
          {...form.register("expected_exam_date")}
        />
        {fieldError(ids.examDate, errors.expected_exam_date?.message)}
      </div>

      <div role="radiogroup" aria-labelledby={ids.goal}>
        <p id={ids.goal} className="mb-2 text-sm font-medium">
          {t("profile.dailyGoal")}
        </p>
        {GOALS.map((goal) => (
          <label key={goal} className="flex min-h-11 items-center gap-3">
            <input type="radio" value={goal} className="size-5" {...form.register("daily_goal")} />
            {t(`profile.goals.${goal}`)}
          </label>
        ))}
      </div>

      <Button type="submit" disabled={pending} className="h-11 self-start">
        {submitLabel}
      </Button>
    </form>
  );
}
