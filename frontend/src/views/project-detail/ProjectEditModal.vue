<script setup>
import DeskSection from "@/components/desk/DeskSection.vue";
import DeskField from "@/components/desk/DeskField.vue";
import DeskInput from "@/components/desk/DeskInput.vue";
import DeskSelect from "@/components/desk/DeskSelect.vue";
import DeskTextarea from "@/components/desk/DeskTextarea.vue";
import { ref } from "vue";
import DeskLinkPicker from "@/components/desk/DeskLinkPicker.vue";
import CustomerCreateModal from "@/components/CustomerCreateModal.vue";
import { __ } from "@/utils/translate";

const props = defineProps({
	open: { type: Boolean, default: false },
	project: { type: Object, default: null },
	editForm: { type: Object, required: true },
	errors: { type: Object, default: () => ({}) },
	isSubproject: { type: Boolean, default: false },
	subsCount: { type: Number, default: 0 },
	isMultiCompany: { type: Boolean, default: false },
});

const emit = defineEmits(["close", "save", "clear-error"]);

const customerModalOpen = ref(false);
const customerPickerKey = ref(0);
function onCustomerCreated(name) {
	props.editForm.client = name;
	emit("clear-error", "client");
	customerPickerKey.value++;
}
</script>

<template>
	<Teleport to="body">
		<div
			v-if="open"
			class="fixed inset-0 bg-ink-900/40 z-[60] flex items-center justify-center p-6"
			@click.self="emit('close')"
		>
			<div
				class="bg-white border border-ink-200 w-full max-w-2xl shadow-fp-lg flex flex-col"
				style="border-radius: 12px; max-height: calc(100vh - 3rem)"
				@click.stop
			>
				<header
					class="px-5 py-3 border-b border-ink-200 flex items-center justify-between flex-shrink-0 bg-white"
					style="border-radius: 12px 12px 0 0"
				>
					<div class="min-w-0 flex-1">
						<h2 class="text-sm font-semibold text-ink-900">
							{{ __("Edit project") }}
						</h2>
						<p class="text-[11px] text-ink-500 mt-0.5 truncate">{{ project?.name }}</p>
					</div>
					<button
						type="button"
						class="text-ink-500 hover:text-ink-900 text-lg leading-none flex-shrink-0 ml-3"
						:aria-label="__('Close')"
						@click="emit('close')"
					>
						x
					</button>
				</header>

				<div class="p-5 overflow-y-auto flex-1">
					<DeskSection :title="__('Basic information')">
						<DeskField :label="__('Project name')" required :error="errors.name">
							<DeskInput
								v-model="editForm.name"
								@input="emit('clear-error', 'name')"
							/>
						</DeskField>
						<DeskField :label="__('Client')" :error="errors.client">
							<div class="flex items-center gap-2">
								<div class="flex-1 min-w-0">
									<DeskLinkPicker
										:key="customerPickerKey"
										v-model="editForm.client"
										doctype="Customer"
										:placeholder="__('Select customer')"
										label-field="customer_name"
										value-field="name"
										:search-fields="['customer_name', 'name']"
										order-by="modified desc"
										:page-length="20"
										:error="errors.client"
										@change="emit('clear-error', 'client')"
									/>
								</div>
								<button
									type="button"
									class="text-xs px-2.5 py-1 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700 whitespace-nowrap"
									style="border-radius: 6px"
									@click="customerModalOpen = true"
								>
									{{ __("+ New") }}
								</button>
							</div>
						</DeskField>
						<DeskField
							:label="__('Project type')"
							:hint="__('Internal or External (ERPNext).')"
						>
							<DeskLinkPicker
								v-model="editForm.projectType"
								doctype="Project Type"
								:placeholder="__('Select project type')"
								label-field="name"
								value-field="name"
								:search-fields="['name']"
								:page-length="20"
							/>
						</DeskField>
						<DeskField :label="__('Category')" :error="errors.type">
							<DeskLinkPicker
								v-model="editForm.type"
								doctype="Project Category"
								:placeholder="__('Select project category')"
								label-field="name"
								value-field="name"
								:search-fields="['category_name', 'name']"
								order-by="sort_order asc"
								:page-length="20"
								:error="errors.type"
								@change="emit('clear-error', 'type')"
							/>
						</DeskField>
						<!-- Company is locked after create (§14). Shown read-only so the user
                 can see which company the project belongs to, but not change it. -->
						<DeskField
							:label="__('Company')"
							:hint="
								__('Locked after create — a project can\'t be moved between companies.')
							"
						>
							<DeskInput :model-value="editForm.company" disabled />
						</DeskField>
						<DeskField :label="__('Location')">
							<DeskInput v-model="editForm.location" />
						</DeskField>
						<DeskField :label="__('Note')">
							<DeskTextarea v-model="editForm.description" :rows="3" />
						</DeskField>
						<DeskField
							v-if="!isSubproject"
							:label="__('Subprojects')"
							:hint="
								subsCount > 0
									? subsCount === 1
										? __(
												'Locked on - this project has {0} subproject. Delete or move them out before turning this off.',
												[subsCount]
											)
										: __(
												'Locked on - this project has {0} subprojects. Delete or move them out before turning this off.',
												[subsCount]
											)
									: __(
											'Turn on to break this project into subprojects (e.g. Block A / Block B / Tower 1).'
										)
							"
						>
							<label
								class="inline-flex items-center gap-2 cursor-pointer select-none"
							>
								<input
									type="checkbox"
									v-model="editForm.isGroup"
									:disabled="subsCount > 0"
									class="accent-brand-600 disabled:cursor-not-allowed"
								/>
								<span class="text-sm text-ink-700"
									>{{ __("Allow subprojects under this project") }}</span
								>
							</label>
						</DeskField>
					</DeskSection>

					<DeskSection :title="__('Schedule & cost')">
						<DeskField :label="__('Start date')">
							<DeskInput v-model="editForm.startDate" type="date" />
						</DeskField>
						<DeskField :label="__('End date')">
							<DeskInput v-model="editForm.endDate" type="date" />
						</DeskField>
						<DeskField :label="__('Budget')" :hint="__('In INR')">
							<DeskInput v-model="editForm.budget" type="number" />
						</DeskField>
						<!-- Progress is the weighted rollup of task progress (server-derived) —
							 not manually editable, so status and progress stay decoupled. -->
					</DeskSection>

					<DeskSection :title="__('Team & status')">
						<DeskField :label="__('Project Manager')" :error="errors.pm">
							<DeskLinkPicker
								v-model="editForm.pm"
								doctype="User"
								:placeholder="__('Select project manager')"
								label-field="full_name"
								value-field="name"
								:search-fields="['full_name', 'name', 'email']"
								:filters="[['enabled', '=', 1]]"
								order-by="full_name asc"
								:page-length="20"
								:error="errors.pm"
								@change="emit('clear-error', 'pm')"
							/>
						</DeskField>
						<DeskField :label="__('Status')">
							<DeskSelect v-model="editForm.status">
								<option value="New">{{ __("New") }}</option>
								<option value="Ongoing">{{ __("Ongoing") }}</option>
								<option value="Delayed">{{ __("Delayed") }}</option>
								<option value="Completed">{{ __("Completed") }}</option>
							</DeskSelect>
						</DeskField>
						<DeskField :label="__('Priority')">
							<DeskSelect v-model="editForm.priority">
								<option value="Low">{{ __("Low") }}</option>
								<option value="Medium">{{ __("Medium") }}</option>
								<option value="High">{{ __("High") }}</option>
							</DeskSelect>
						</DeskField>
					</DeskSection>
				</div>

				<footer
					class="px-5 py-3 border-t border-ink-200 flex items-center justify-end gap-2 flex-shrink-0 bg-white"
					style="border-radius: 0 0 12px 12px"
				>
					<button
						type="button"
						class="text-xs px-3 py-1.5 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700"
						style="border-radius: 6px"
						@click="emit('close')"
					>
						{{ __("Cancel") }}
					</button>
					<button type="button" class="desk-save-btn" @click="emit('save')">
						{{ __("Save") }}
					</button>
				</footer>
			</div>
		</div>

		<CustomerCreateModal
			:open="customerModalOpen"
			@close="customerModalOpen = false"
			@created="onCustomerCreated"
		/>
	</Teleport>
</template>
