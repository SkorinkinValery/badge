import { Flex } from "@mantine/core";

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <Flex justify="center" align="center" mih="100vh">
      {children}
    </Flex>
  );
}
