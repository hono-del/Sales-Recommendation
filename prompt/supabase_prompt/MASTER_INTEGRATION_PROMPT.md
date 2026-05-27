# 🚀 Supabase + Clerk 完全統合プロンプト

このプロンプトは、Next.js App Router プロジェクトに Supabase データベースと Clerk 認証を完全に統合するための包括的なガイドです。

---

## 📋 実行前の確認事項

AIアシスタントへ：このプロンプトを実行する前に、以下を確認してください：

1. ✅ Next.js プロジェクトが App Router を使用している
2. ✅ `/docs/` フォルダ内に設計ドキュメントが存在する
3. ✅ 以下のベストプラクティスファイルを読み込み済み：
   - `clerk_setupprpompt.md`
   - `supabase_bootstrap_nextjs_app_with_SupabaseAuth.md`
   - `supabase_migration_prompt.md`
   - `supabase_postgres_SQL_Style_guide.md`
   - `supabase_realtime_AIprompt.md`

---

## 🎯 AI実行フェーズ

### フェーズ 1️⃣: プロジェクト設計の理解と分析

**タスク：プロジェクト設計ドキュメントの検索と読み込み**

```
1. `/docs/` フォルダ内から以下のファイルを検索：
   - system_architecture.md
   - system_design.md
   - database_design.md
   - db_schema.md
   - requirements.yaml
   - requirements.md
   - または類似の設計ドキュメント

2. 見つかったすべてのドキュメントを読み込み、以下を抽出：
   - データベーステーブル構造
   - リレーションシップ
   - 認証要件
   - ユーザーロールとパーミッション
   - 必要な RLS ポリシー
   - リアルタイム機能の有無

3. 設計ドキュメントが見つからない場合：
   - ユーザーに通知し、最低限の情報（テーブル構造など）を尋ねる
   - 暫定的な基本構造を提案する
```

**出力：設計分析サマリー**

ユーザーに以下の形式でサマリーを提示：

```markdown
## 📊 プロジェクト設計分析結果

### データベース構造
- テーブル数: X個
- 主要テーブル:
  - [テーブル名] - [説明]
  - ...

### 認証要件
- 認証方式: [Google OAuth / Email / その他]
- ユーザーロール: [あり/なし]
- 必要な RLS ポリシー: [リスト]

### リアルタイム機能
- 必要性: [あり/なし]
- 対象テーブル: [リスト]

この内容で実装を進めてよろしいでしょうか？
問題があれば修正内容をお知らせください。
```

---

### フェーズ 2️⃣: 依存パッケージのインストール

**タスク：必要なパッケージをインストール**

```bash
# Clerk のインストール
npm install @clerk/nextjs@latest

# Supabase のインストール
npm install @supabase/supabase-js@latest @supabase/ssr@latest

# 型定義（必要に応じて）
npm install -D @types/node
```

**実行コマンドを生成し、ターミナルで実行**

---

### フェーズ 3️⃣: 環境変数テンプレートの作成

**タスク：`.env.local.example` ファイルを作成**

プロジェクトルートに以下のファイルを作成：

```env
# Clerk Configuration
# 取得方法: https://dashboard.clerk.com/ → プロジェクト → API Keys
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
CLERK_SECRET_KEY=sk_test_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Clerk Redirect URLs (必要に応じて調整)
NEXT_PUBLIC_CLERK_SIGN_IN_URL=/sign-in
NEXT_PUBLIC_CLERK_SIGN_UP_URL=/sign-up
NEXT_PUBLIC_CLERK_AFTER_SIGN_IN_URL=/
NEXT_PUBLIC_CLERK_AFTER_SIGN_UP_URL=/

# Supabase Configuration
# 取得方法: https://supabase.com/dashboard → プロジェクト → Settings → API
NEXT_PUBLIC_SUPABASE_URL=https://xxxxxxxxxxxxx.supabase.co
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# Database Connection (ローカル開発用 - オプション)
DATABASE_URL=postgresql://postgres:postgres@localhost:54322/postgres
```

**ユーザーへの指示を生成**

---

### フェーズ 4️⃣: Clerk 統合の実装

**重要：`clerk_setupprpompt.md` のベストプラクティスに厳密に従うこと**

#### 4-1. Middleware の作成

`middleware.ts` を作成（`src/` ディレクトリがある場合はその中、なければルートに）：

```typescript
import { clerkMiddleware } from '@clerk/nextjs/server'

export default clerkMiddleware()

export const config = {
  matcher: [
    // Skip Next.js internals and all static files, unless found in search params
    '/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)',
    // Always run for API routes
    '/(api|trpc)(.*)',
  ],
}
```

#### 4-2. Layout の更新

`app/layout.tsx` を更新：

```typescript
import type { Metadata } from "next";
import {
  ClerkProvider,
  SignInButton,
  SignUpButton,
  SignedIn,
  SignedOut,
  UserButton,
} from "@clerk/nextjs";
import "./globals.css";

export const metadata: Metadata = {
  title: "Your App Title",
  description: "Your App Description",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <ClerkProvider>
      <html lang="ja">
        <body>
          <header>
            <SignedOut>
              <SignInButton />
              <SignUpButton />
            </SignedOut>
            <SignedIn>
              <UserButton />
            </SignedIn>
          </header>
          {children}
        </body>
      </html>
    </ClerkProvider>
  );
}
```

**検証：以下を確認**
- ✅ `clerkMiddleware()` を使用（`authMiddleware()` ではない）
- ✅ `<ClerkProvider>` でアプリをラップ
- ✅ `@clerk/nextjs` からインポート
- ✅ App Router 構造を使用

---

### フェーズ 5️⃣: Supabase クライアントの実装

**重要：`supabase_bootstrap_nextjs_app_with_SupabaseAuth.md` のベストプラクティスに厳密に従うこと**

#### 5-1. ディレクトリ構造の作成

```bash
mkdir -p lib/supabase
```

#### 5-2. ブラウザクライアントの作成

`lib/supabase/client.ts` を作成：

```typescript
import { createBrowserClient } from '@supabase/ssr'

export function createClient() {
  return createBrowserClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY!
  )
}
```

#### 5-3. サーバークライアントの作成

`lib/supabase/server.ts` を作成：

```typescript
import { createServerClient } from '@supabase/ssr'
import { cookies } from 'next/headers'

export async function createClient() {
  const cookieStore = await cookies()

  return createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY!,
    {
      cookies: {
        getAll() {
          return cookieStore.getAll()
        },
        setAll(cookiesToSet) {
          try {
            cookiesToSet.forEach(({ name, value, options }) =>
              cookieStore.set(name, value, options)
            )
          } catch {
            // The `setAll` method was called from a Server Component.
            // This can be ignored if you have middleware refreshing
            // user sessions.
          }
        },
      },
    }
  )
}
```

#### 5-4. Middleware の統合（Clerk + Supabase）

既存の `middleware.ts` を更新して Supabase を統合：

```typescript
import { clerkMiddleware } from '@clerk/nextjs/server'
import { createServerClient } from '@supabase/ssr'
import { NextResponse, type NextRequest } from 'next/server'

export default clerkMiddleware(async (auth, request: NextRequest) => {
  // Supabase セッション更新
  let supabaseResponse = NextResponse.next({
    request,
  })

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY!,
    {
      cookies: {
        getAll() {
          return request.cookies.getAll()
        },
        setAll(cookiesToSet) {
          cookiesToSet.forEach(({ name, value }) => request.cookies.set(name, value))
          supabaseResponse = NextResponse.next({
            request,
          })
          cookiesToSet.forEach(({ name, value, options }) =>
            supabaseResponse.cookies.set(name, value, options)
          )
        },
      },
    }
  )

  // Supabase ユーザーセッションの確認
  await supabase.auth.getUser()

  return supabaseResponse
})

export const config = {
  matcher: [
    '/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)',
    '/(api|trpc)(.*)',
  ],
}
```

**検証：以下を確認**
- ✅ `@supabase/ssr` を使用（`auth-helpers-nextjs` ではない）
- ✅ `getAll()` と `setAll()` のみを使用（`get`、`set`、`remove` は使用しない）
- ✅ `cookies()` を `await` で呼び出し

---

### フェーズ 6️⃣: データベースマイグレーションの生成

**重要：`supabase_migration_prompt.md` と `supabase_postgres_SQL_Style_guide.md` に従うこと**

#### 6-1. Supabase ディレクトリ構造の作成

```bash
mkdir -p supabase/migrations
```

#### 6-2. マイグレーションファイルの生成

フェーズ1で抽出した設計ドキュメントに基づいて、各テーブルのマイグレーションファイルを作成：

**ファイル名規則：** `YYYYMMDDHHmmss_short_description.sql`

例：`supabase/migrations/20250101120000_create_initial_schema.sql`

```sql
-- ============================================
-- Migration: 初期スキーマ作成
-- Purpose: [プロジェクト名] の基本テーブル構造を作成
-- Tables: [テーブルリスト]
-- ============================================

-- テーブル作成
create table public.users (
  id uuid primary key default gen_random_uuid(),
  clerk_user_id text unique not null,
  email text not null,
  full_name text,
  created_at timestamptz default now() not null,
  updated_at timestamptz default now() not null
);
comment on table public.users is 'アプリケーションのユーザー情報を管理';

-- RLS の有効化
alter table public.users enable row level security;

-- RLS ポリシー: SELECT
create policy "users_select_own_data" on public.users
  for select to authenticated
  using (clerk_user_id = auth.jwt() ->> 'sub');

-- RLS ポリシー: INSERT
create policy "users_insert_own_data" on public.users
  for insert to authenticated
  with check (clerk_user_id = auth.jwt() ->> 'sub');

-- RLS ポリシー: UPDATE
create policy "users_update_own_data" on public.users
  for update to authenticated
  using (clerk_user_id = auth.jwt() ->> 'sub')
  with check (clerk_user_id = auth.jwt() ->> 'sub');

-- インデックスの作成
create index idx_users_clerk_user_id on public.users(clerk_user_id);

-- [設計ドキュメントに基づいて、すべてのテーブルに対して上記を繰り返す]
```

**各テーブルに対して：**
1. テーブル作成（小文字、snake_case、複数形）
2. コメント追加
3. RLS 有効化
4. RLS ポリシー作成（SELECT、INSERT、UPDATE、DELETE）
5. 必要なインデックス作成

#### 6-3. Clerk ユーザー同期の実装（オプションだが推奨）

`supabase/migrations/[timestamp]_create_clerk_webhook_handler.sql`:

```sql
-- ============================================
-- Migration: Clerk Webhook ハンドラー
-- Purpose: Clerk のユーザー作成時に Supabase users テーブルへ同期
-- ============================================

create or replace function public.handle_clerk_user_created()
returns trigger
security definer
set search_path = public
language plpgsql
as $$
begin
  insert into public.users (clerk_user_id, email, full_name)
  values (
    new.id,
    new.email,
    new.first_name || ' ' || new.last_name
  );
  return new;
end;
$$;

-- [注: 実際の実装は Clerk Webhook を使用することを推奨]
```

---

### フェーズ 7️⃣: Supabase Realtime の実装（必要な場合）

**重要：`supabase_realtime_AIprompt.md` のベストプラクティスに従うこと**

設計ドキュメントでリアルタイム機能が必要な場合のみ実行：

#### 7-1. Database Triggers の作成

例：メッセージテーブルのリアルタイム更新

`supabase/migrations/[timestamp]_create_realtime_triggers.sql`:

```sql
-- ============================================
-- Migration: Realtime Triggers
-- Purpose: broadcast を使用したリアルタイム更新の実装
-- ============================================

create or replace function public.broadcast_message_changes()
returns trigger
security definer
language plpgsql
as $$
begin
  perform realtime.broadcast_changes(
    'room:' || coalesce(new.room_id, old.room_id)::text,
    tg_op,
    tg_op,
    tg_table_name,
    tg_table_schema,
    new,
    old
  );
  return coalesce(new, old);
end;
$$;

-- Trigger の作成
create trigger messages_realtime_trigger
  after insert or update or delete on public.messages
  for each row execute function public.broadcast_message_changes();

-- realtime.messages テーブルの RLS ポリシー
create policy "users_can_receive_broadcasts" on realtime.messages
  for select to authenticated
  using (
    topic like 'room:%' and
    exists (
      select 1 from public.room_members
      where user_id = auth.uid()
      and room_id = split_part(topic, ':', 2)::uuid
    )
  );

-- パフォーマンス用インデックス
create index idx_room_members_user_room 
  on public.room_members(user_id, room_id);
```

#### 7-2. クライアント実装のサンプル

`lib/supabase/realtime.ts`:

```typescript
'use client'

import { useEffect, useRef } from 'react'
import { createClient } from './client'

export function useRealtimeChannel(
  roomId: string,
  onMessage: (message: any) => void
) {
  const channelRef = useRef<any>(null)

  useEffect(() => {
    const supabase = createClient()

    // 既存のサブスクリプションをチェック
    if (channelRef.current?.state === 'subscribed') return

    const channel = supabase.channel(`room:${roomId}:messages`, {
      config: { private: true }
    })

    channelRef.current = channel

    channel
      .on('broadcast', { event: 'INSERT' }, (payload) => {
        onMessage(payload)
      })
      .subscribe()

    return () => {
      if (channelRef.current) {
        supabase.removeChannel(channelRef.current)
        channelRef.current = null
      }
    }
  }, [roomId, onMessage])
}
```

---

### フェーズ 8️⃣: 型定義の生成（TypeScript）

`lib/supabase/types.ts` を作成：

```typescript
// Supabase の型定義
// 実際の型は supabase gen types typescript を使用して生成することを推奨

export type Json =
  | string
  | number
  | boolean
  | null
  | { [key: string]: Json | undefined }
  | Json[]

export interface Database {
  public: {
    Tables: {
      users: {
        Row: {
          id: string
          clerk_user_id: string
          email: string
          full_name: string | null
          created_at: string
          updated_at: string
        }
        Insert: {
          id?: string
          clerk_user_id: string
          email: string
          full_name?: string | null
          created_at?: string
          updated_at?: string
        }
        Update: {
          id?: string
          clerk_user_id?: string
          email?: string
          full_name?: string | null
          created_at?: string
          updated_at?: string
        }
      }
      // [設計ドキュメントに基づいて、すべてのテーブルの型を生成]
    }
  }
}
```

---

### フェーズ 9️⃣: ユーティリティ関数の作成

#### 9-1. Clerk ユーザー取得ユーティリティ

`lib/clerk/utils.ts`:

```typescript
import { auth, currentUser } from '@clerk/nextjs/server'

export async function getCurrentUserId() {
  const { userId } = await auth()
  return userId
}

export async function getCurrentUser() {
  return await currentUser()
}
```

#### 9-2. Supabase + Clerk 連携ユーティリティ

`lib/supabase/auth-helpers.ts`:

```typescript
import { auth } from '@clerk/nextjs/server'
import { createClient } from './server'

export async function getSupabaseUserByClerkId() {
  const { userId } = await auth()
  if (!userId) return null

  const supabase = await createClient()
  const { data, error } = await supabase
    .from('users')
    .select('*')
    .eq('clerk_user_id', userId)
    .single()

  if (error) return null
  return data
}

export async function createSupabaseUserFromClerk() {
  const { userId } = await auth()
  if (!userId) throw new Error('Unauthorized')

  const user = await currentUser()
  if (!user) throw new Error('User not found')

  const supabase = await createClient()
  const { data, error } = await supabase
    .from('users')
    .insert({
      clerk_user_id: userId,
      email: user.emailAddresses[0].emailAddress,
      full_name: `${user.firstName} ${user.lastName}`,
    })
    .select()
    .single()

  if (error) throw error
  return data
}
```

---

### フェーズ 🔟: フロントエンド実装（認証UI + データ操作）

**重要：既存のフロントエンドに認証機能とデータ操作UIを統合**

このフェーズでは、ユーザーが既に作成した React/Next.js のフロントエンドに実用的な認証機能とデータベース操作の実装を追加します。

**📄 詳細な実装手順は `FRONTEND_IMPLEMENTATION_ADDON.md` を参照してください。**

#### 実装する内容のサマリー：

1. **認証ページ**
   - サインイン/サインアップページ（Clerk UI コンポーネント使用）
   - カスタマイズ可能な外観設定

2. **Protected Routes**
   - Server Component での保護（`auth()` 使用）
   - Client Component での保護（`useUser()` 使用）

3. **ナビゲーション**
   - ヘッダーコンポーネント（ログイン状態に応じた表示切替）
   - モバイル対応

4. **Server Actions**
   - CRUD 操作の実装（設計ドキュメントに基づく）
   - バリデーション（zod 使用）
   - エラーハンドリング

5. **UI コンポーネント**
   - フォームコンポーネント
   - リスト表示コンポーネント
   - 削除確認ダイアログ

6. **カスタムフック**
   - `useSupabaseUser` - Supabase ユーザー情報取得
   - `useSupabaseQuery` - 汎用クエリフック

7. **リアルタイム機能**（必要な場合）
   - メッセージコンポーネント
   - リアルタイム更新

8. **ローディング・エラー UI**
   - `loading.tsx` - スケルトンローディング
   - `error.tsx` - エラー表示とリトライ
   - `not-found.tsx` - 404 ページ

9. **ユーザーオンボーディング**
   - Clerk Webhook エンドポイント
   - 自動ユーザー同期

**実装を開始するには：**

```
@supabase_prompt/FRONTEND_IMPLEMENTATION_ADDON.md を読み込んで、
フェーズ 10 の詳細な実装手順に従ってください。
```

---

### フェーズ 1️⃣1️⃣: 実装の検証とテスト

以下の検証を自動的に実行：

1. **ファイル構造の確認**
```
✅ middleware.ts が存在
✅ app/layout.tsx が ClerkProvider でラップされている
✅ lib/supabase/client.ts が存在
✅ lib/supabase/server.ts が存在
✅ supabase/migrations/ にマイグレーションファイルが存在
✅ .env.local.example が存在
✅ app/sign-in/[[...sign-in]]/page.tsx が存在
✅ app/sign-up/[[...sign-up]]/page.tsx が存在
✅ components/header.tsx が存在
✅ app/actions/ にServer Actionsが存在（該当する場合）
✅ Webhook エンドポイントが存在
```

2. **コードパターンの検証**
```
✅ clerkMiddleware() を使用（authMiddleware ではない）
✅ createBrowserClient / createServerClient を使用
✅ getAll() / setAll() を使用（get/set/remove ではない）
✅ @supabase/ssr を使用（auth-helpers-nextjs ではない）
✅ useUser() / auth() を適切に使用
✅ Server Actions で revalidatePath() を使用
✅ フォームでバリデーションを実装
```

3. **SQL の検証**
```
✅ すべてのテーブルで RLS が有効化されている
✅ 各操作（SELECT/INSERT/UPDATE/DELETE）に対してポリシーが存在
✅ 小文字の SQL を使用
✅ コメントが含まれている
```

4. **UI/UX の検証**
```
✅ 認証済み/未認証でUIが適切に切り替わる
✅ Protected routes が実装されている
✅ ローディング状態が実装されている
✅ エラーハンドリングが実装されている
✅ フォームにバリデーションがある
✅ レスポンシブデザインに対応
```

---

## 👤 ユーザー実行フェーズ

AIが実装を完了したら、以下の指示をユーザーに提示：

### ステップ 1: Clerk の設定

1. **Clerk Dashboard にアクセス**
   - https://dashboard.clerk.com/ を開く
   - 新しいプロジェクトを作成（または既存のプロジェクトを選択）

2. **Google OAuth の有効化**
   - サイドバーから「Configure」→「SSO Connections」
   - 「Google」を選択して有効化
   - Google Cloud Console で OAuth 2.0 クライアント ID を作成（必要な場合）

3. **API Keys の取得**
   - サイドバーから「API Keys」を選択
   - 以下をコピー：
     - `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`
     - `CLERK_SECRET_KEY`

4. **Redirect URLs の設定**
   - 「Paths」セクションで以下を設定：
     - Sign-in URL: `/sign-in`
     - Sign-up URL: `/sign-up`
     - After sign-in: `/`
     - After sign-up: `/`

### ステップ 2: Supabase の設定

1. **Supabase Dashboard にアクセス**
   - https://supabase.com/dashboard を開く
   - 新しいプロジェクトを作成

2. **プロジェクト設定を待つ**
   - プロジェクトのプロビジョニングが完了するまで待機（約2分）

3. **API Keys の取得**
   - サイドバーから「Settings」→「API」
   - 以下をコピー：
     - `Project URL` → `NEXT_PUBLIC_SUPABASE_URL`
     - `anon public` → `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY`
     - `service_role` → `SUPABASE_SERVICE_ROLE_KEY` (⚠️ 秘密情報！)

4. **マイグレーションの実行**
   
   **オプション A: SQL Editor を使用（推奨）**
   - Supabase Dashboard の「SQL Editor」を開く
   - `supabase/migrations/` 内の各 `.sql` ファイルの内容をコピー
   - SQL Editor に貼り付けて実行（順番に）

   **オプション B: Supabase CLI を使用**
   ```bash
   # Supabase CLI のインストール
   npm install -g supabase
   
   # Supabase プロジェクトとリンク
   supabase link --project-ref your-project-ref
   
   # マイグレーションの実行
   supabase db push
   ```

### ステップ 3: 環境変数の設定

1. **`.env.local` ファイルを作成**
   - プロジェクトルートに `.env.local` ファイルを作成
   - `.env.local.example` の内容をコピー

2. **取得した値を貼り付け**
   ```env
   # Clerk (ステップ1で取得)
   NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_xxxxx
   CLERK_SECRET_KEY=sk_test_xxxxx
   
   # Clerk Redirect URLs
   NEXT_PUBLIC_CLERK_SIGN_IN_URL=/sign-in
   NEXT_PUBLIC_CLERK_SIGN_UP_URL=/sign-up
   NEXT_PUBLIC_CLERK_AFTER_SIGN_IN_URL=/
   NEXT_PUBLIC_CLERK_AFTER_SIGN_UP_URL=/
   
   # Supabase (ステップ2で取得)
   NEXT_PUBLIC_SUPABASE_URL=https://xxxxx.supabase.co
   NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=eyJhbGciOi...
   SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOi...
   ```

3. **`.env.local` が `.gitignore` に含まれていることを確認**
   ```
   # .gitignore
   .env*.local
   ```

### ステップ 4: 動作確認

1. **開発サーバーの起動**
   ```bash
   npm run dev
   ```

2. **ブラウザで確認**
   - http://localhost:3000 を開く
   - サインアップボタンが表示されることを確認
   - Google でサインアップ/サインインを試す

3. **データベース確認**
   - Supabase Dashboard の「Table Editor」を開く
   - `users` テーブルにログインしたユーザーが追加されているか確認

4. **トラブルシューティング**
   
   **問題：サインインできない**
   - Clerk Dashboard の「Logs」でエラーを確認
   - 環境変数が正しく設定されているか確認
   - Redirect URLs が一致しているか確認

   **問題：Supabase に接続できない**
   - 環境変数の URL とキーを再確認
   - ブラウザのコンソールでエラーメッセージを確認
   - Network タブで API リクエストを確認

   **問題：RLS エラーが発生**
   - Supabase Dashboard の「Logs」を確認
   - RLS ポリシーが正しく設定されているか確認
   - `auth.jwt()` が正しく動作しているか確認

### ステップ 5: 本番環境へのデプロイ（Vercel の例）

1. **Vercel にプロジェクトをデプロイ**
   ```bash
   npm install -g vercel
   vercel
   ```

2. **環境変数の設定**
   - Vercel Dashboard でプロジェクトを開く
   - 「Settings」→「Environment Variables」
   - `.env.local` の内容をすべて追加

3. **Clerk の本番環境設定**
   - Clerk Dashboard で本番環境の Redirect URLs を設定
   - `https://your-domain.vercel.app` を追加

4. **Supabase の本番環境設定**
   - 必要に応じて RLS ポリシーを調整
   - Realtime を使用する場合、設定を確認

---

## 📚 完了後のドキュメント

実装完了後、以下のドキュメントを自動生成：

### `docs/INTEGRATION_COMPLETE.md`

```markdown
# ✅ Supabase + Clerk 統合完了レポート

実装日: [日付]

## 📦 インストールされたパッケージ

- @clerk/nextjs: [バージョン]
- @supabase/supabase-js: [バージョン]
- @supabase/ssr: [バージョン]

## 🗄️ データベース構造

### 作成されたテーブル
[テーブルリスト]

### マイグレーションファイル
[ファイルリスト]

## 🔐 認証フロー

[認証フローの説明]

## 🔌 API エンドポイント（実装された場合）

[エンドポイントリスト]

## 📝 次のステップ

1. [ ] Clerk Webhooks の設定（ユーザー同期の自動化）
2. [ ] 追加の RLS ポリシーの実装
3. [ ] Realtime 機能のテスト
4. [ ] ユニットテストの作成

## 🐛 既知の問題・制限事項

[あれば記載]

## 📖 参考リソース

- [Clerk Documentation](https://clerk.com/docs)
- [Supabase Documentation](https://supabase.com/docs)
- [Next.js App Router](https://nextjs.org/docs/app)
```

---

## 🚨 重要な注意事項

### セキュリティ

1. **環境変数の管理**
   - `SUPABASE_SERVICE_ROLE_KEY` は絶対に公開しない
   - `.env.local` は Git にコミットしない
   - 本番環境では環境変数を適切に設定

2. **RLS ポリシー**
   - すべてのテーブルで RLS を有効化
   - 適切なポリシーを設定し、不要なデータアクセスを防ぐ
   - テストアカウントで各ポリシーを検証

3. **API Keys**
   - `NEXT_PUBLIC_*` プレフィックスの変数はクライアント側に公開される
   - 秘密情報は `NEXT_PUBLIC_` を付けない

### パフォーマンス

1. **インデックス**
   - RLS ポリシーで使用するカラムにインデックスを作成
   - 外部キーにもインデックスを作成

2. **クエリの最適化**
   - 必要なカラムのみを SELECT
   - ページネーションを実装

### スケーラビリティ

1. **Realtime の使用**
   - 必要な場合のみ Realtime を有効化
   - 適切なトピック名を使用してスコープを限定

2. **Database Connection Pool**
   - Supabase Dashboard で接続プールサイズを調整

---

## 🎓 追加学習リソース

- Clerk + Supabase 統合ガイド: https://clerk.com/docs/integrations/databases/supabase
- Next.js App Router ベストプラクティス: https://nextjs.org/docs/app/building-your-application
- Supabase RLS ガイド: https://supabase.com/docs/guides/auth/row-level-security

---

## ✅ 最終チェックリスト

AIアシスタントとして、実装前に以下を確認：

- [ ] すべてのベストプラクティスファイルを読み込んだ
- [ ] 設計ドキュメントを正しく解析した
- [ ] Clerk の最新パターンを使用している（clerkMiddleware）
- [ ] Supabase の最新パターンを使用している（@supabase/ssr）
- [ ] すべてのテーブルで RLS を有効化した
- [ ] 適切な RLS ポリシーを作成した
- [ ] インデックスを作成した
- [ ] 型定義を生成した
- [ ] ユーザー向けの詳細な指示を生成した
- [ ] エラーハンドリングを実装した

実装完了後：

- [ ] 統合レポートを生成した
- [ ] ユーザーに次のステップを明示した
- [ ] トラブルシューティングガイドを提供した

---

**このプロンプトを使用して、AIアシスタントに以下のように指示してください：**

```
上記のプロンプトに従って、このプロジェクトに Supabase と Clerk を完全に統合してください。
設計ドキュメントは /docs/ フォルダにあります。
すべてのベストプラクティスに従い、実装完了後はユーザー向けの詳細な指示を生成してください。
```

