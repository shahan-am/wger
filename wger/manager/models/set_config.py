#  This file is part of wger Workout Manager <https://github.com/wger-project>.
#  Copyright (C) 2013 - 2021 wger Team
#
#  wger Workout Manager is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Affero General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  wger Workout Manager is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Affero General Public License for more details.
#
#  You should have received a copy of the GNU Affero General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.

# Django
from django.db import models
from django.utils.translation import gettext_lazy as _

# wger
from wger.core.models import (
    RepetitionUnit,
    WeightUnit,
)
from wger.exercises.models import ExerciseBase
from wger.manager.dataclasses import SetConfigData
from wger.manager.models.abstract_config import (
    AbstractChangeConfig,
    OperationChoices,
    StepChoices,
)


class SetConfig(models.Model):
    """
    Set configuration for an exercise (weight, reps, etc.)
    """

    set = models.ForeignKey(
        'Set',
        verbose_name=_('Sets'),
        on_delete=models.CASCADE,
    )

    exercise = models.ForeignKey(
        ExerciseBase,
        on_delete=models.CASCADE,
    )

    repetition_unit = models.ForeignKey(
        RepetitionUnit,
        default=1,
        on_delete=models.CASCADE,
    )
    """
    The repetition unit of a set. This can be e.g. a repetition, a minute, etc.
    """

    weight_unit = models.ForeignKey(
        WeightUnit,
        verbose_name=_('Unit'),
        default=1,
        on_delete=models.CASCADE,
    )
    """
    The weight unit of a set. This can be e.g. kg, lb, km/h, etc.
    """

    order = models.PositiveIntegerField(
        blank=True,
    )

    comment = models.CharField(
        max_length=100,
        blank=True,
    )

    # Metaclass to set some other properties
    class Meta:
        ordering = [
            'order',
            'id',
        ]

    def get_owner_object(self):
        """
        Returns the object that has owner information
        """
        return self.set.exerciseday.training

    def calculate_config_value(self, configs: list[AbstractChangeConfig]):
        out = 0

        for config in configs:
            if config.replace:
                out = config.value
                continue

            step = config.value if config.step == StepChoices.ABSOLUTE else out * config.value / 100

            if config.operation == OperationChoices.PLUS:
                out += step
            else:
                out -= step

        return out

    def get_config(self, iteration: int):
        max_iter_weight = 1
        max_iter_reps = 1

        for i in range(1, iteration + 1):
            weight = self.get_weight(max_iter_weight)
            reps = self.get_reps(max_iter_reps)

            log_data = self.workoutlog_set.filter(iteration=i - 1)

            # If any of the entries in last log is greater than the last config data,
            # proceed. Otherwise, the weight won't change
            if log_data.exists():
                for log in log_data:
                    if log.weight >= weight and log.reps >= reps:
                        max_iter_weight = i
                        max_iter_reps = i

                    # As soon as we find a log that we didn't make, stop
                    else:
                        break

        return SetConfigData(
            weight=self.get_weight(max_iter_weight),
            reps=self.get_reps(max_iter_reps),
            rir=self.get_rir(iteration),
            rest=self.get_rest(iteration),
        )

    def get_weight(self, iteration: int):
        return self.calculate_config_value(self.weightconfig_set.filter(iteration__lte=iteration))

    def get_reps(self, iteration: int):
        return self.calculate_config_value(self.repsconfig_set.filter(iteration__lte=iteration))

    def get_rir(self, iteration: int):
        return self.calculate_config_value(self.rirconfig_set.filter(iteration__lte=iteration))

    def get_rest(self, iteration: int):
        return self.calculate_config_value(self.restconfig_set.filter(iteration__lte=iteration))
