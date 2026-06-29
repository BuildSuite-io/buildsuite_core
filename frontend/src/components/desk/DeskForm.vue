<script setup>
// Form-page layout for Desk-styled forms. Sticky save bar region at the top with a
// thin border below it; scrollable body below.
//
// The action-bar slot sticks at `top: 48px` (matching the DeskShell topbar's h-12)
// when this form is rendered inside DeskShell — the standard case. If you render
// DeskForm outside DeskShell, override the sticky offset at the call site.
//
// Composition:
//   <DeskPage title="…">
//     <DeskForm>
//       <template #action-bar>
//         <DeskActionBar @save="…" @cancel="…" />
//       </template>
//       <DeskSection title="…"> … </DeskSection>
//     </DeskForm>
//   </DeskPage>
</script>

<template>
	<form @submit.prevent>
		<div
			v-if="$slots['action-bar']"
			class="sticky z-10 bg-white border-b border-ink-200"
			style="top: 48px"
		>
			<slot name="action-bar" />
		</div>
		<div class="pt-4">
			<slot />
		</div>
	</form>
</template>
