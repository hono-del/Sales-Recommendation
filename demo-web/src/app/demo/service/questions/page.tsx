import { DemoProgressNav } from "@/components/demo/DemoProgressNav";
import { ServiceQuestionsClient } from "@/components/demo/ServiceQuestionsClient";

export default function ServiceQuestionsPage() {
  return (
    <>
      <DemoProgressNav currentStep={2} />
      <ServiceQuestionsClient />
    </>
  );
}
