import { DemoProgressNav } from "@/components/demo/DemoProgressNav";
import { QuestionsClient } from "@/components/demo/QuestionsClient";

export default function QuestionsPage() {
  return (
    <>
      <DemoProgressNav currentStep={2} />
      <QuestionsClient />
    </>
  );
}
